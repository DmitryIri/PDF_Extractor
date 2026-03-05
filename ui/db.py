"""
ui/db.py — SQLite database layer for PDF Extractor UI.

Stores run history: status, export paths, error messages.
DB file lives outside the repo: /srv/pdf-extractor/db/runs.db
"""

import sqlite3
from contextlib import contextmanager
from pathlib import Path
from typing import Generator, Optional

DB_PATH = Path("/srv/pdf-extractor/db/runs.db")


def init_db() -> None:
    """Create DB file and schema on first run."""
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    with get_conn() as conn:
        conn.execute("""
            CREATE TABLE IF NOT EXISTS runs (
                run_id            TEXT PRIMARY KEY,
                journal_code      TEXT NOT NULL,
                issue_id          TEXT NOT NULL,
                original_filename TEXT NOT NULL,
                inbox_pdf_path    TEXT NOT NULL,
                status            TEXT NOT NULL,
                export_path       TEXT,
                zip_path          TEXT,
                total_articles    INTEGER,
                pid               INTEGER,
                exit_code         INTEGER,
                error_msg         TEXT,
                log_path          TEXT NOT NULL,
                created_at        TEXT NOT NULL,
                finished_at       TEXT
            )
        """)


@contextmanager
def get_conn() -> Generator[sqlite3.Connection, None, None]:
    conn = sqlite3.connect(str(DB_PATH))
    conn.row_factory = sqlite3.Row
    try:
        yield conn
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()


def create_run(
    run_id: str,
    journal_code: str,
    issue_id: str,
    original_filename: str,
    inbox_pdf_path: str,
    log_path: str,
    created_at: str,
) -> None:
    with get_conn() as conn:
        conn.execute(
            """
            INSERT INTO runs
              (run_id, journal_code, issue_id, original_filename,
               inbox_pdf_path, status, log_path, created_at)
            VALUES (?, ?, ?, ?, ?, 'pending', ?, ?)
            """,
            (run_id, journal_code, issue_id, original_filename,
             inbox_pdf_path, log_path, created_at),
        )


def get_run(run_id: str) -> Optional[sqlite3.Row]:
    with get_conn() as conn:
        return conn.execute(
            "SELECT * FROM runs WHERE run_id=?", (run_id,)
        ).fetchone()


def get_active_run() -> Optional[sqlite3.Row]:
    """Return first run with status pending or running (single-flight guard)."""
    with get_conn() as conn:
        return conn.execute(
            "SELECT * FROM runs WHERE status IN ('pending','running') LIMIT 1"
        ).fetchone()


def get_recent_runs(limit: int = 20) -> list:
    with get_conn() as conn:
        return conn.execute(
            "SELECT * FROM runs ORDER BY created_at DESC LIMIT ?", (limit,)
        ).fetchall()


def update_run(**kwargs) -> None:
    """Update any columns of a run by run_id."""
    run_id = kwargs.pop("run_id")
    if not kwargs:
        return
    cols = ", ".join(f"{k}=?" for k in kwargs)
    vals = list(kwargs.values()) + [run_id]
    with get_conn() as conn:
        conn.execute(f"UPDATE runs SET {cols} WHERE run_id=?", vals)


def fail_orphaned_runs(finished_at: str) -> None:
    """Mark pending/running runs as failed on app restart (orphaned tasks)."""
    with get_conn() as conn:
        conn.execute(
            """
            UPDATE runs
               SET status='failed',
                   error_msg='Сервис перезапущен — задача была прервана',
                   finished_at=?
             WHERE status IN ('pending','running')
            """,
            (finished_at,),
        )
