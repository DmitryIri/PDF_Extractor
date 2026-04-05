"""
ui/main.py — FastAPI application for PDF Extractor UI.

Routes:
  GET  /                         Upload form
  POST /upload                   Receive PDF, launch pipeline
  GET  /runs/{run_id}            Status page (HTMX polling)
  GET  /api/runs/{run_id}/status HTMX partial (status card)
  GET  /api/runs/{run_id}/download  Stream ZIP download
  GET  /history                  Recent runs list
"""

import asyncio
import logging
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import quote

import aiofiles
from fastapi import FastAPI, File, Form, HTTPException, Request, UploadFile
from fastapi.responses import FileResponse, HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates

from ui.db import (
    create_run,
    fail_orphaned_runs,
    get_active_run,
    get_recent_runs,
    get_run,
    init_db,
)
from ui.pipeline import (
    expected_filename_prefix,
    make_log_path,
    make_run_id,
    parse_issue_id,
    run_pipeline_bg,
)

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(name)s — %(message)s",
)
logger = logging.getLogger(__name__)

INBOX_DIR = Path("/srv/pdf-extractor/inbox")
MAX_UPLOAD_BYTES = 300 * 1024 * 1024  # 300 MB

KNOWN_JOURNALS = ["Mg", "Mh", "Na"]

app = FastAPI(title="PDF Extractor UI", docs_url=None, redoc_url=None)

_templates_dir = Path(__file__).parent / "templates"
templates = Jinja2Templates(directory=str(_templates_dir))

# Custom Jinja2 filter: extract filename from path
templates.env.filters["basename"] = lambda p: Path(p).name if p else ""


def _plural_articles(n: int) -> str:
    """Russian plural for 'статья': 1 статья, 2 статьи, 5 статей."""
    n = abs(n) % 100
    if 11 <= n <= 19:
        return "статей"
    n1 = n % 10
    if n1 == 1:
        return "статья"
    if 2 <= n1 <= 4:
        return "статьи"
    return "статей"


templates.env.filters["plural_articles"] = _plural_articles


# ---------------------------------------------------------------------------
# Startup
# ---------------------------------------------------------------------------

@app.on_event("startup")
async def startup() -> None:
    init_db()
    INBOX_DIR.mkdir(parents=True, exist_ok=True)
    # Any run left pending/running from a previous process is orphaned — mark failed
    fail_orphaned_runs(datetime.now(timezone.utc).isoformat())
    logger.info("PDF Extractor UI started on 127.0.0.1:8080")


# ---------------------------------------------------------------------------
# Pages
# ---------------------------------------------------------------------------

@app.get("/", response_class=HTMLResponse)
async def index(request: Request, error: str = "") -> HTMLResponse:
    return templates.TemplateResponse("index.html", {
        "request": request,
        "journals": KNOWN_JOURNALS,
        "error": error,
    })


@app.post("/upload")
async def upload(
    request: Request,
    journal_code: str = Form(...),
    issue_id: str = Form(...),
    pdf_file: UploadFile = File(...),
) -> RedirectResponse:

    journal_code = journal_code.strip()
    issue_id = issue_id.strip().lower()

    # ── 1. Single-flight guard ──────────────────────────────────────────────
    active = get_active_run()
    if active:
        active_id = active["run_id"]
        return RedirectResponse(
            f"/runs/{active_id}?error="
            + quote("Уже выполняется другой запуск. Дождитесь завершения."),
            status_code=303,
        )

    # ── 2. Validate issue_id format ─────────────────────────────────────────
    try:
        parse_issue_id(issue_id, journal_code)
    except ValueError as e:
        return RedirectResponse(
            f"/?error={quote(str(e))}", status_code=303
        )

    # ── 3. Validate filename ────────────────────────────────────────────────
    filename = pdf_file.filename or ""
    if not filename.lower().endswith(".pdf"):
        return RedirectResponse(
            f"/?error={quote('Принимаются только файлы с расширением .pdf')}",
            status_code=303,
        )

    expected_prefix = expected_filename_prefix(journal_code, issue_id)
    if not filename.startswith(expected_prefix):
        msg = (
            f"Имя файла '{filename}' не соответствует выбранному журналу/выпуску. "
            f"Ожидается файл, начинающийся с '{expected_prefix}' "
            f"(например {expected_prefix}.pdf)"
        )
        return RedirectResponse(f"/?error={quote(msg)}", status_code=303)

    # ── 4. Save PDF to inbox (streaming, size-limited) ──────────────────────
    run_id = make_run_id()
    safe_filename = f"{expected_prefix}.pdf"
    inbox_path = INBOX_DIR / safe_filename

    total_bytes = 0
    try:
        async with aiofiles.open(inbox_path, "wb") as out:
            while True:
                chunk = await pdf_file.read(65536)  # 64 KB chunks
                if not chunk:
                    break
                total_bytes += len(chunk)
                if total_bytes > MAX_UPLOAD_BYTES:
                    inbox_path.unlink(missing_ok=True)
                    return RedirectResponse(
                        f"/?error={quote('Файл слишком большой (максимум 300 MB)')}",
                        status_code=303,
                    )
                await out.write(chunk)
    except Exception as e:
        inbox_path.unlink(missing_ok=True)
        logger.exception("Error saving uploaded file")
        return RedirectResponse(
            f"/?error={quote(f'Ошибка сохранения файла: {e}')}",
            status_code=303,
        )

    # ── 5. Create DB record ─────────────────────────────────────────────────
    log_path = make_log_path(run_id)
    created_at = datetime.now(timezone.utc).isoformat()

    create_run(
        run_id=run_id,
        journal_code=journal_code,
        issue_id=issue_id,
        original_filename=filename,
        inbox_pdf_path=str(inbox_path),
        log_path=log_path,
        created_at=created_at,
    )

    # ── 6. Launch pipeline in background ───────────────────────────────────
    asyncio.create_task(
        run_pipeline_bg(
            run_id=run_id,
            journal_code=journal_code,
            issue_id=issue_id,
            pdf_path=str(inbox_path),
            log_path=log_path,
        )
    )
    logger.info(f"[{run_id}] Task created — redirecting to /runs/{run_id}")

    return RedirectResponse(f"/runs/{run_id}", status_code=303)


@app.get("/runs/{run_id}", response_class=HTMLResponse)
async def run_page(request: Request, run_id: str, error: str = "") -> HTMLResponse:
    run = get_run(run_id)
    if run is None:
        raise HTTPException(status_code=404, detail="Run not found")
    return templates.TemplateResponse("run.html", {
        "request": request,
        "run": dict(run),
        "error": error,
    })


@app.get("/history", response_class=HTMLResponse)
async def history(request: Request) -> HTMLResponse:
    runs = get_recent_runs(20)
    return templates.TemplateResponse("history.html", {
        "request": request,
        "runs": [dict(r) for r in runs],
    })


# ---------------------------------------------------------------------------
# API (HTMX partials + file download)
# ---------------------------------------------------------------------------

@app.get("/api/runs/{run_id}/status", response_class=HTMLResponse)
async def run_status_partial(request: Request, run_id: str) -> HTMLResponse:
    run = get_run(run_id)
    if run is None:
        raise HTTPException(status_code=404, detail="Run not found")
    return templates.TemplateResponse("partials/status_card.html", {
        "request": request,
        "run": dict(run),
    })


@app.get("/api/runs/{run_id}/download")
async def download_zip(run_id: str) -> FileResponse:
    run = get_run(run_id)
    if run is None:
        raise HTTPException(status_code=404, detail="Run not found")
    if run["status"] != "done":
        raise HTTPException(status_code=400, detail="Run not completed yet")
    zip_path = run["zip_path"]
    if not zip_path or not Path(zip_path).exists():
        raise HTTPException(status_code=404, detail="ZIP file not found")
    return FileResponse(
        path=zip_path,
        media_type="application/zip",
        filename=Path(zip_path).name,
    )
