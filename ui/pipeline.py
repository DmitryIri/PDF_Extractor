"""
ui/pipeline.py — Background pipeline runner for PDF Extractor UI.

Launches tools/run_issue_pipeline.sh via asyncio.create_subprocess_exec,
tracks status in SQLite, builds export ZIP on success.
"""

import asyncio
import json
import logging
import zipfile
from datetime import datetime, timezone
from pathlib import Path

from ui.db import update_run

logger = logging.getLogger(__name__)

REPO = Path("/opt/projects/pdf-extractor")
RUNS_ROOT = Path("/srv/pdf-extractor/runs")
LOGS_DIR = Path("/srv/pdf-extractor/logs/ui_runs")
RUN_TIMEOUT = 6 * 3600  # 6 hours


# ---------------------------------------------------------------------------
# Issue ID / filename helpers
# ---------------------------------------------------------------------------

def parse_issue_id(issue_id: str, journal_code: str) -> tuple[str, str]:
    """
    Parse issue_id like 'mg_2025_12' into ('2025', '12').
    Validates that the prefix matches journal_code (case-insensitive).

    Raises ValueError with a user-friendly message on any mismatch.
    """
    parts = issue_id.strip().split("_")
    if len(parts) != 3:
        raise ValueError(
            f"Неверный формат ID выпуска '{issue_id}'. "
            "Ожидается: {{код}}_{ГГГГ}_{ММ}, например mg_2025_12"
        )
    code, year, month = parts
    if code.lower() != journal_code.strip().lower():
        raise ValueError(
            f"Префикс ID выпуска '{code}' не совпадает с кодом журнала "
            f"'{journal_code}'. Ожидается: {journal_code.lower()}_{year}_{month}"
        )
    if not (year.isdigit() and len(year) == 4):
        raise ValueError(f"Год в ID выпуска должен быть 4-значным числом, получено: '{year}'")
    if not (month.isdigit() and 1 <= int(month) <= 12):
        raise ValueError(f"Месяц в ID выпуска должен быть 01–12, получено: '{month}'")
    return year, month


def expected_filename_prefix(journal_code: str, issue_id: str) -> str:
    """
    Build the expected PDF filename prefix from journal_code + issue_id.
    Example: ('Mg', 'mg_2025_12') → 'Mg_2025-12'
    """
    year, month = parse_issue_id(issue_id, journal_code)
    return f"{journal_code.strip()}_{year}-{month}"


def make_run_id() -> str:
    now = datetime.now(timezone.utc)
    return f"ui_{now.strftime('%Y_%m_%d__%H_%M_%S')}"


def make_log_path(run_id: str) -> str:
    LOGS_DIR.mkdir(parents=True, exist_ok=True)
    return str(LOGS_DIR / f"{run_id}.log")


# ---------------------------------------------------------------------------
# ZIP builder
# ---------------------------------------------------------------------------

def build_zip(export_path: Path, issue_prefix: str) -> Path:
    """
    Package the export directory into a ZIP archive.

    Archive structure (flat, sha256sum-compatible):
        articles/*.pdf
        manifest/export_manifest.json
        checksums.sha256
        README.md

    ZIP is written inside export_path itself so each run keeps its own archive.
    Returns the ZIP path.
    """
    zip_path = export_path / f"{issue_prefix}_export.zip"
    with zipfile.ZipFile(zip_path, "w", zipfile.ZIP_DEFLATED) as zf:
        articles_dir = export_path / "articles"
        for pdf in sorted(articles_dir.glob("*.pdf")):
            zf.write(pdf, f"articles/{pdf.name}")

        manifest = export_path / "manifest" / "export_manifest.json"
        if manifest.exists():
            zf.write(manifest, "manifest/export_manifest.json")

        checksums = export_path / "checksums.sha256"
        if checksums.exists():
            zf.write(checksums, "checksums.sha256")

        readme = export_path / "README.md"
        if readme.exists():
            zf.write(readme, "README.md")

    return zip_path


# ---------------------------------------------------------------------------
# Background pipeline runner
# ---------------------------------------------------------------------------

async def run_pipeline_bg(
    run_id: str,
    journal_code: str,
    issue_id: str,
    pdf_path: str,
    log_path: str,
) -> None:
    """
    Async background task: runs tools/run_issue_pipeline.sh,
    updates DB status at each stage, builds ZIP on success.
    """
    cmd = [
        "/bin/bash",
        str(REPO / "tools/run_issue_pipeline.sh"),
        "--journal-code", journal_code,
        "--issue-id", issue_id,
        "--pdf-path", pdf_path,
        "--run-id", run_id,
    ]

    logger.info(f"[{run_id}] Starting pipeline: {' '.join(cmd)}")

    try:
        with open(log_path, "w") as log_file:
            proc = await asyncio.create_subprocess_exec(
                *cmd,
                stdout=log_file,
                stderr=log_file,
                cwd=str(REPO),
            )

            update_run(run_id=run_id, status="running", pid=proc.pid)
            logger.info(f"[{run_id}] pid={proc.pid}")

            try:
                exit_code = await asyncio.wait_for(proc.wait(), timeout=RUN_TIMEOUT)
            except asyncio.TimeoutError:
                proc.kill()
                await proc.wait()
                logger.error(f"[{run_id}] Timeout after {RUN_TIMEOUT}s — killed")
                update_run(
                    run_id=run_id,
                    status="failed",
                    exit_code=-1,
                    error_msg="Таймаут (6 часов) — процесс принудительно остановлен",
                    finished_at=datetime.now(timezone.utc).isoformat(),
                )
                return

        finished_at = datetime.now(timezone.utc).isoformat()
        logger.info(f"[{run_id}] exit_code={exit_code}")

        if exit_code == 0:
            _handle_success(run_id, journal_code, issue_id, finished_at)
        else:
            update_run(
                run_id=run_id,
                status="failed",
                exit_code=exit_code,
                error_msg=f"Pipeline завершился с ошибкой (exit code {exit_code})",
                finished_at=finished_at,
            )

    except Exception as e:
        logger.exception(f"[{run_id}] Unexpected error in run_pipeline_bg")
        update_run(
            run_id=run_id,
            status="failed",
            exit_code=-1,
            error_msg=f"Внутренняя ошибка: {e}",
            finished_at=datetime.now(timezone.utc).isoformat(),
        )


def _handle_success(
    run_id: str,
    journal_code: str,
    issue_id: str,
    finished_at: str,
) -> None:
    """Read 07.json, build ZIP, update DB to done."""
    outputs_dir = RUNS_ROOT / f"{issue_id}_{run_id}" / "outputs"
    output_07 = outputs_dir / "07.json"

    try:
        raw = json.loads(output_07.read_text())
        export_path_str: str = raw["data"]["export_path"]
        total_articles: int = raw["data"]["total_articles"]
    except Exception as e:
        logger.error(f"[{run_id}] Cannot read 07.json: {e}")
        update_run(
            run_id=run_id,
            status="failed",
            exit_code=0,
            error_msg=f"Ошибка чтения результатов pipeline: {e}",
            finished_at=finished_at,
        )
        return

    export_path = Path(export_path_str)
    if not export_path.exists():
        update_run(
            run_id=run_id,
            status="failed",
            exit_code=0,
            error_msg=f"Директория экспорта не найдена: {export_path_str}",
            finished_at=finished_at,
        )
        return

    try:
        issue_prefix = expected_filename_prefix(journal_code, issue_id)
        zip_path = build_zip(export_path, issue_prefix)
        logger.info(f"[{run_id}] ZIP built: {zip_path}")
    except Exception as e:
        logger.error(f"[{run_id}] ZIP build failed: {e}")
        update_run(
            run_id=run_id,
            status="failed",
            exit_code=0,
            error_msg=f"Ошибка сборки ZIP: {e}",
            finished_at=finished_at,
        )
        return

    update_run(
        run_id=run_id,
        status="done",
        export_path=export_path_str,
        zip_path=str(zip_path),
        total_articles=total_articles,
        exit_code=0,
        finished_at=finished_at,
    )
