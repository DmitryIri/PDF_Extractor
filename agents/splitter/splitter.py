#!/usr/bin/env python3
# PDF Extractor — Splitter
# Physical PDF splitting by ready-made boundary ranges (from BoundaryDetector).
# DOES NOT determine boundaries - only executes given ranges.
#
# Contract:
# - stdin: JSON envelope (or raw) with pdf_path + boundary_ranges
# - stdout (fd1): JSON envelope with article_pdfs list
# - stderr (fd2): logs only, no JSON
# - exit codes: 0=success, 10=invalid_input, 20=pdf_not_found, 40=split_failed, 50=internal_error

from __future__ import annotations

import hashlib
import json
import os
import sys
from pathlib import Path
from typing import Any, Dict, List, Optional

import fitz  # PyMuPDF

COMPONENT = "Splitter"
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


def _validate_range(rng: Dict[str, Any], idx: int) -> None:
    """Validate single boundary range structure."""
    required = ["id", "from", "to"]
    for field in required:
        if field not in rng:
            _error_exit(10, "invalid_input", f"Range {idx}: missing field '{field}'", {"range": rng})

    if not isinstance(rng["id"], str) or not rng["id"]:
        _error_exit(10, "invalid_input", f"Range {idx}: 'id' must be non-empty string", {"range": rng})

    if not isinstance(rng["from"], int) or not isinstance(rng["to"], int):
        _error_exit(10, "invalid_input", f"Range {idx}: 'from' and 'to' must be integers", {"range": rng})

    if rng["from"] < 1 or rng["to"] < 1:
        _error_exit(10, "invalid_input", f"Range {idx}: pages must be >= 1 (1-indexed)", {"range": rng})

    if rng["from"] > rng["to"]:
        _error_exit(10, "invalid_input", f"Range {idx}: 'from' must be <= 'to'", {"range": rng})


def _compute_sha256(file_path: Path) -> str:
    """Compute SHA256 hash of file."""
    sha256 = hashlib.sha256()
    with open(file_path, "rb") as f:
        while chunk := f.read(8192):
            sha256.update(chunk)
    return sha256.hexdigest()


def _split_pdf(
    pdf_path: Path,
    issue_id: str,
    boundary_ranges: List[Dict[str, Any]],
    output_dir: Path,
) -> List[Dict[str, Any]]:
    """
    Split PDF by boundary ranges.

    Returns list of article_pdfs with metadata.
    """
    # Open source PDF
    try:
        doc = fitz.open(pdf_path)
        total_pages = doc.page_count
    except Exception as e:
        _error_exit(20, "pdf_not_found", f"Cannot open PDF: {e}", {"pdf_path": str(pdf_path)})

    # Create output directory
    output_dir.mkdir(parents=True, exist_ok=True)

    article_pdfs = []

    for idx, rng in enumerate(boundary_ranges):
        article_id = rng["id"]
        from_page = rng["from"]
        to_page = rng["to"]

        # Validate page range against PDF
        if from_page > total_pages or to_page > total_pages:
            doc.close()
            _error_exit(
                40,
                "range_out_of_bounds",
                f"Range {article_id}: pages {from_page}-{to_page} exceed PDF page count {total_pages}",
                {"article_id": article_id, "from": from_page, "to": to_page, "total_pages": total_pages}
            )

        # Output filename: {issue_id}_{article_id}.pdf
        output_filename = f"{issue_id}_{article_id}.pdf"
        output_path = output_dir / output_filename
        temp_path = output_dir / f".{output_filename}.tmp"

        try:
            # Create new PDF with extracted pages
            # PyMuPDF uses 0-indexed pages, our ranges are 1-indexed
            output_doc = fitz.open()
            output_doc.insert_pdf(doc, from_page=from_page - 1, to_page=to_page - 1)

            # Clear metadata for determinism (remove timestamps)
            output_doc.set_metadata({})

            # Write to temp file first (atomic write)
            # Use options for maximum determinism:
            # - deflate=True: compress streams
            # - garbage=4: maximum garbage collection
            # - clean=True: sanitize/clean
            # - no_new_id=True: don't generate new document ID
            output_doc.save(
                str(temp_path),
                deflate=True,
                garbage=4,
                clean=True,
                no_new_id=True,
            )
            output_doc.close()

            # Atomic rename
            temp_path.rename(output_path)

            # Compute metadata
            file_size = output_path.stat().st_size
            sha256_hash = _compute_sha256(output_path)

            article_pdfs.append({
                "id": article_id,
                "path": str(output_path),
                "from_page": from_page,
                "to_page": to_page,
                "page_count": to_page - from_page + 1,
                "file_size_bytes": file_size,
                "sha256": sha256_hash,
            })

        except Exception as e:
            doc.close()
            # Clean up temp file if exists
            if temp_path.exists():
                temp_path.unlink()
            _error_exit(
                40,
                "split_failed",
                f"Failed to split pages {from_page}-{to_page} for article {article_id}: {e}",
                {"article_id": article_id, "exception": str(e)}
            )

    doc.close()
    return article_pdfs


def main() -> None:
    # Read and parse stdin
    try:
        raw = sys.stdin.read()
        data = json.loads(raw)
    except Exception as e:
        _error_exit(10, "invalid_input", f"Invalid JSON on stdin: {e}")

    # Unwrap envelope (TechSpec v_2_5 §5)
    payload = data.get("data", data) if isinstance(data, dict) else data

    # Validate required fields
    try:
        pdf_path_str = payload["pdf_path"]
        boundary_ranges = payload["boundary_ranges"]
        issue_id = payload.get("issue_id", "unknown")
        output_dir_str = payload.get("output_dir")

        if not isinstance(pdf_path_str, str) or not pdf_path_str:
            raise ValueError("pdf_path must be non-empty string")
        if not isinstance(boundary_ranges, list):
            raise ValueError("boundary_ranges must be a list")
        if not isinstance(issue_id, str) or not issue_id:
            raise ValueError("issue_id must be non-empty string")

    except KeyError as e:
        _error_exit(10, "invalid_input", f"Missing required field: {e}")
    except ValueError as e:
        _error_exit(10, "invalid_input", str(e))

    # Determine output directory
    if output_dir_str:
        output_dir = Path(output_dir_str)
    else:
        # Default: same directory as source PDF + /articles/
        pdf_path = Path(pdf_path_str)
        output_dir = pdf_path.parent / "articles"

    # Validate PDF path
    pdf_path = Path(pdf_path_str)
    if not pdf_path.exists():
        _error_exit(20, "pdf_not_found", f"PDF file not found: {pdf_path_str}", {"pdf_path": pdf_path_str})
    if not pdf_path.is_file():
        _error_exit(20, "pdf_not_found", f"PDF path is not a file: {pdf_path_str}", {"pdf_path": pdf_path_str})

    # Validate boundary ranges
    if len(boundary_ranges) == 0:
        # Empty ranges is valid but produces 0 articles
        article_pdfs = []
    else:
        for idx, rng in enumerate(boundary_ranges):
            _validate_range(rng, idx)

        # Split PDF
        article_pdfs = _split_pdf(pdf_path, issue_id, boundary_ranges, output_dir)

    # Success envelope
    out = {
        "status": "success",
        "component": COMPONENT,
        "version": VERSION,
        "data": {
            "issue_id": issue_id,
            "pdf_path": str(pdf_path),
            "output_dir": str(output_dir),
            "total_articles": len(article_pdfs),
            "article_pdfs": article_pdfs,
        },
        "error": None,
    }

    json_bytes = (json.dumps(out, ensure_ascii=False, indent=2) + "\n").encode("utf-8")
    os.write(1, json_bytes)


if __name__ == "__main__":
    main()
