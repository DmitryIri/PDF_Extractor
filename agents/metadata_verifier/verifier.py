#!/usr/bin/env python3
# PDF Extractor — MetadataVerifier
# Verify and enrich article manifest for OutputBuilder readiness.
#
# Contract:
# - stdin: JSON envelope (or raw) with article manifest
# - stdout (fd1): JSON envelope with VerifiedArticleManifest
# - stderr (fd2): logs only, no JSON
# - exit codes: 0=success, 10=invalid_input, 30=verification_failed, 50=internal_error

from __future__ import annotations

import hashlib
import json
import os
import re
import sys
from pathlib import Path
from typing import Any, Dict, List, Optional

COMPONENT = "MetadataVerifier"
VERSION = "1.0.0"


def _error_exit(exit_code: int, code: str, message: str, details: Optional[Dict[str, Any]] = None) -> None:
    """Emit error envelope to stdout and exit."""
    out = {
        "status": "error",
        "component": COMPONENT,
        "version": VERSION,
        "data": None,
        "error": {"exit_code": exit_code, "code": code, "message": message, "details": details or {}},
    }
    json_bytes = (json.dumps(out, ensure_ascii=False) + "\n").encode("utf-8")
    os.write(1, json_bytes)
    raise SystemExit(exit_code)


def _compute_sha256(file_path: Path) -> str:
    """Compute SHA256 hash of file."""
    sha256 = hashlib.sha256()
    with open(file_path, "rb") as f:
        while chunk := f.read(8192):
            sha256.update(chunk)
    return sha256.hexdigest()


def _sanitize_surname(surname: str) -> str:
    """Sanitize author surname for filename: allow [A-Za-z0-9_-], collapse multiple underscores."""
    # Replace any character not in [A-Za-z0-9_-] with underscore
    sanitized = re.sub(r'[^A-Za-z0-9_-]', '_', surname)
    # Collapse multiple underscores into one
    sanitized = re.sub(r'_+', '_', sanitized)
    # Strip leading/trailing underscores
    sanitized = sanitized.strip('_')
    return sanitized


def _extract_journal_code(issue_prefix: str) -> str:
    """Extract journal code from issue_prefix (first 2 letters before underscore)."""
    # Expected format: Mg_2025-12
    parts = issue_prefix.split('_')
    if len(parts) < 1:
        _error_exit(10, "invalid_input", f"Cannot extract journal_code from issue_prefix: {issue_prefix}")
    journal_code = parts[0]
    if len(journal_code) != 2:
        _error_exit(10, "invalid_input", f"Journal code must be exactly 2 letters: {journal_code}")
    return journal_code


def _verify_and_enrich_article(
    article: Dict[str, Any],
    issue_prefix: str,
    idx: int
) -> Dict[str, Any]:
    """Verify and enrich a single article entry."""
    # Validate required input fields
    required_fields = ["article_id", "from_page", "to_page", "first_author_surname", "path"]
    for field in required_fields:
        if field not in article:
            _error_exit(10, "invalid_input", f"Article {idx}: missing required field '{field}'")

    article_id = article["article_id"]
    from_page = article["from_page"]
    to_page = article["to_page"]
    first_author_surname = article["first_author_surname"]
    splitter_path = article["path"]

    # Validate types
    if not isinstance(from_page, int) or not isinstance(to_page, int):
        _error_exit(10, "invalid_input", f"Article {article_id}: from_page and to_page must be integers")

    if from_page < 1 or to_page < 1:
        _error_exit(30, "verification_failed", f"Article {article_id}: page numbers must be >= 1")

    if from_page > to_page:
        _error_exit(30, "verification_failed", f"Article {article_id}: from_page must be <= to_page")

    if not isinstance(first_author_surname, str) or not first_author_surname:
        _error_exit(10, "invalid_input", f"Article {article_id}: first_author_surname must be non-empty string")

    # Sanitize surname
    sanitized_surname = _sanitize_surname(first_author_surname)
    if not sanitized_surname:
        _error_exit(30, "verification_failed",
                    f"Article {article_id}: first_author_surname '{first_author_surname}' is empty after sanitization")

    # Format page numbers as 3-digit zero-padded
    from_page_formatted = str(from_page).zfill(3)
    to_page_formatted = str(to_page).zfill(3)

    # Build expected_filename: <IssuePrefix>_<PPP-PPP>_<Surname>.pdf
    expected_filename = f"{issue_prefix}_{from_page_formatted}-{to_page_formatted}_{sanitized_surname}.pdf"

    # Verify splitter_path exists
    splitter_path_obj = Path(splitter_path)
    if not splitter_path_obj.exists():
        _error_exit(30, "verification_failed", f"Article {article_id}: splitter output file does not exist: {splitter_path}")

    if not splitter_path_obj.is_file():
        _error_exit(30, "verification_failed", f"Article {article_id}: splitter output path is not a file: {splitter_path}")

    # Get file size
    file_size = splitter_path_obj.stat().st_size
    if file_size == 0:
        _error_exit(30, "verification_failed", f"Article {article_id}: splitter output file has zero size")

    # Compute SHA256
    sha256_hash = _compute_sha256(splitter_path_obj)

    # Build enriched article
    enriched = {
        "article_id": article_id,
        "from_page": from_page,
        "to_page": to_page,
        "first_author_surname": sanitized_surname,
        "expected_filename": expected_filename,
        "splitter_output": {
            "path": str(splitter_path_obj),
            "bytes": file_size,
            "sha256": sha256_hash
        }
    }

    return enriched


def main() -> None:
    # Read stdin
    try:
        raw = json.load(sys.stdin)
    except Exception as e:
        _error_exit(10, "invalid_input", f"Invalid JSON on stdin: {e}")

    # Unwrap envelope
    payload = raw.get("data", raw) if isinstance(raw, dict) else raw

    # Validate required top-level fields
    try:
        issue_id = payload.get("issue_id")
        pdf_path = payload.get("pdf_path")
        article_pdfs = payload.get("article_pdfs")

        if not issue_id:
            raise ValueError("issue_id is required")
        if not pdf_path:
            raise ValueError("pdf_path is required")
        if article_pdfs is None:
            raise ValueError("article_pdfs is required")
        if not isinstance(article_pdfs, list):
            raise ValueError("article_pdfs must be a list")

    except (KeyError, ValueError) as e:
        _error_exit(10, "invalid_input", str(e))

    # Extract issue_prefix from pdf_path
    pdf_path_obj = Path(pdf_path)
    issue_prefix = pdf_path_obj.stem  # filename without extension

    # Validate issue_prefix matches source PDF basename
    if not issue_prefix:
        _error_exit(30, "verification_failed", "Cannot extract issue_prefix from pdf_path")

    # Extract journal_code
    journal_code = _extract_journal_code(issue_prefix)

    # Validate articles count > 0
    if len(article_pdfs) == 0:
        _error_exit(30, "verification_failed", "No articles in manifest (articles count must be > 0)")

    # Verify and enrich each article (deterministic order by article_id)
    articles_sorted = sorted(article_pdfs, key=lambda a: a.get("article_id", ""))

    verified_articles = []
    for idx, article in enumerate(articles_sorted):
        enriched = _verify_and_enrich_article(article, issue_prefix, idx)
        verified_articles.append(enriched)

    # Determine run_id (if present in payload, use it; otherwise derive from issue_id)
    run_id = payload.get("run_id", f"run_{issue_id}")

    # Build VerifiedArticleManifest
    verified_manifest = {
        "journal_code": journal_code,
        "issue_prefix": issue_prefix,
        "source_pdf": {
            "path": str(pdf_path)
        },
        "run": {
            "run_id": run_id
        },
        "total_articles": len(verified_articles),
        "articles": verified_articles
    }

    # Success envelope
    out = {
        "status": "success",
        "component": COMPONENT,
        "version": VERSION,
        "data": verified_manifest,
        "error": None
    }

    # Emit JSON to stdout (deterministic: sort_keys, separators)
    json_bytes = (json.dumps(out, ensure_ascii=False, sort_keys=True, separators=(',', ':')) + "\n").encode("utf-8")
    os.write(1, json_bytes)


if __name__ == "__main__":
    try:
        main()
    except SystemExit:
        raise
    except Exception as e:
        _error_exit(50, "internal_error", f"Unexpected error: {e}", {"exception": str(e)})
