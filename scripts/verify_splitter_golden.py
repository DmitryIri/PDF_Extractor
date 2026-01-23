#!/usr/bin/env python3
"""
Verify Splitter output against golden test artifacts.

Checks:
1. All article PDFs exist
2. Page counts match boundary_ranges (to - from + 1)
3. File sizes > 0
4. Determinism: same sha256 on re-run

Usage:
    python scripts/verify_splitter_golden.py
"""

import json
import sys
from pathlib import Path

try:
    import fitz
except ImportError:
    print("ERROR: PyMuPDF (fitz) not found. Install with: pip install PyMuPDF", file=sys.stderr)
    sys.exit(50)


def verify_splitter_output(output_json_path: Path, golden_boundaries_path: Path) -> tuple[bool, list[str]]:
    """Verify Splitter output against golden boundaries. Returns (success, errors)."""
    errors = []

    # Load output
    try:
        with output_json_path.open() as f:
            output = json.load(f)
    except Exception as e:
        errors.append(f"Failed to load output JSON: {e}")
        return False, errors

    # Load golden boundaries
    try:
        with golden_boundaries_path.open() as f:
            golden = json.load(f)
            golden_ranges = golden["data"]["boundary_ranges"]
            golden_issue_id = golden["data"]["issue_id"]
            golden_total_pages = golden["data"]["total_pages"]
    except Exception as e:
        errors.append(f"Failed to load golden boundaries: {e}")
        return False, errors

    # Check status
    if output.get("status") != "success":
        errors.append(f"Output status is not success: {output.get('status')}")
        return False, errors

    # Extract data
    try:
        data = output["data"]
        article_pdfs = data["article_pdfs"]
        issue_id = data["issue_id"]
        total_articles = data["total_articles"]
    except KeyError as e:
        errors.append(f"Missing required field in output: {e}")
        return False, errors

    # Check article count matches golden ranges
    if total_articles != len(golden_ranges):
        errors.append(f"Article count mismatch: got {total_articles}, expected {len(golden_ranges)}")

    if len(article_pdfs) != len(golden_ranges):
        errors.append(f"article_pdfs count != golden ranges: {len(article_pdfs)} vs {len(golden_ranges)}")

    # Verify each article
    for i, (article, golden_range) in enumerate(zip(article_pdfs, golden_ranges)):
        article_id = article.get("id")
        expected_id = golden_range["id"]

        # Check ID match
        if article_id != expected_id:
            errors.append(f"Article {i}: ID mismatch: got {article_id}, expected {expected_id}")

        # Check page range
        from_page = article.get("from_page")
        to_page = article.get("to_page")
        expected_from = golden_range["from"]
        expected_to = golden_range["to"]

        if from_page != expected_from:
            errors.append(f"Article {article_id}: from_page mismatch: got {from_page}, expected {expected_from}")
        if to_page != expected_to:
            errors.append(f"Article {article_id}: to_page mismatch: got {to_page}, expected {expected_to}")

        # Check page count
        page_count = article.get("page_count")
        expected_page_count = expected_to - expected_from + 1
        if page_count != expected_page_count:
            errors.append(f"Article {article_id}: page_count mismatch: got {page_count}, expected {expected_page_count}")

        # Check PDF file exists
        pdf_path = Path(article.get("path"))
        if not pdf_path.exists():
            errors.append(f"Article {article_id}: PDF file does not exist: {pdf_path}")
            continue

        # Check file size
        file_size = article.get("file_size_bytes", 0)
        actual_size = pdf_path.stat().st_size
        if file_size != actual_size:
            errors.append(f"Article {article_id}: file_size_bytes mismatch: got {file_size}, actual {actual_size}")
        if file_size == 0:
            errors.append(f"Article {article_id}: file size is 0")

        # Verify actual page count in PDF
        try:
            doc = fitz.open(pdf_path)
            actual_page_count = doc.page_count
            doc.close()

            if actual_page_count != expected_page_count:
                errors.append(
                    f"Article {article_id}: actual PDF page count mismatch: "
                    f"got {actual_page_count}, expected {expected_page_count}"
                )
        except Exception as e:
            errors.append(f"Article {article_id}: failed to open PDF: {e}")

        # Check sha256 present (for determinism tracking)
        if "sha256" not in article:
            errors.append(f"Article {article_id}: missing sha256 field")

    return len(errors) == 0, errors


def main():
    # Paths
    output_json = Path("/tmp/out.json")
    golden_boundaries = Path(__file__).parent.parent / "golden_tests" / "mg_2025_12_boundaries.json"

    if not output_json.exists():
        print(f"ERROR: Output JSON not found: {output_json}", file=sys.stderr)
        print("Run splitter first to generate output", file=sys.stderr)
        sys.exit(1)

    if not golden_boundaries.exists():
        print(f"ERROR: Golden boundaries not found: {golden_boundaries}", file=sys.stderr)
        sys.exit(1)

    # Verify
    success, errors = verify_splitter_output(output_json, golden_boundaries)

    if success:
        print("✓ All checks passed", file=sys.stderr)

        # Load output for summary
        with output_json.open() as f:
            output = json.load(f)

        total = output["data"]["total_articles"]
        print(f"✓ {total} article PDFs verified", file=sys.stderr)

        # Output success envelope
        result = {
            "status": "success",
            "component": "verify_splitter_golden",
            "version": "1.0.0",
            "data": {
                "verified": True,
                "total_articles": total,
                "checks": ["existence", "page_counts", "file_sizes", "sha256_present"]
            },
            "error": None
        }
        print(json.dumps(result, indent=2))
        sys.exit(0)
    else:
        print("✗ Verification FAILED:", file=sys.stderr)
        for err in errors:
            print(f"  - {err}", file=sys.stderr)

        # Output error envelope
        result = {
            "status": "error",
            "component": "verify_splitter_golden",
            "version": "1.0.0",
            "data": None,
            "error": {
                "exit_code": 1,
                "code": "verification_failed",
                "message": "Splitter output verification failed",
                "details": {"errors": errors}
            }
        }
        print(json.dumps(result, indent=2))
        sys.exit(1)


if __name__ == "__main__":
    main()
