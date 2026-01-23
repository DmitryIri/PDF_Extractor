#!/usr/bin/env python3
"""
Verify BoundaryDetector output against golden test artifacts.

Checks:
1. Article starts match golden_tests/mg_2025_12_article_starts.json (start_page list)
2. Confidence == 1.0 for all article_starts (typography-based detection)
3. Boundary ranges invariants:
   - contiguous (range[i].to + 1 == range[i+1].from)
   - non-overlapping
   - last range.to == total_pages
   - range.from == article_starts[i].start_page

Usage:
    cat boundaries.json | python scripts/verify_boundary_detector_golden.py
    python scripts/verify_boundary_detector_golden.py < boundaries.json
"""

import json
import sys
from pathlib import Path


def verify_boundaries(boundaries: dict, golden_starts: dict) -> tuple[bool, list[str]]:
    """Verify boundaries against golden and invariants. Returns (success, errors)."""
    errors = []

    # Extract data
    try:
        issue_id = boundaries["data"]["issue_id"]
        total_pages = boundaries["data"]["total_pages"]
        article_starts = boundaries["data"]["article_starts"]
        boundary_ranges = boundaries["data"]["boundary_ranges"]
    except KeyError as e:
        errors.append(f"Missing required field: {e}")
        return False, errors

    # Check 1: Issue ID and total_pages match golden
    if issue_id != golden_starts["issue_id"]:
        errors.append(f"Issue ID mismatch: got {issue_id}, expected {golden_starts['issue_id']}")
    if total_pages != golden_starts["total_pages"]:
        errors.append(f"Total pages mismatch: got {total_pages}, expected {golden_starts['total_pages']}")

    # Check 2: Article starts count matches golden
    golden_start_pages = [s["start_page"] for s in golden_starts["article_starts"]]
    actual_start_pages = [s["start_page"] for s in article_starts]

    if len(actual_start_pages) != len(golden_start_pages):
        errors.append(f"Article count mismatch: got {len(actual_start_pages)}, expected {len(golden_start_pages)}")

    # Check 3: Start pages match golden exactly
    if actual_start_pages != golden_start_pages:
        errors.append(f"Start pages mismatch:\n  got: {actual_start_pages}\n  expected: {golden_start_pages}")

    # Check 4: Confidence == 1.0 for all starts (typography-based is deterministic)
    for i, start in enumerate(article_starts):
        if start.get("confidence") != 1.0:
            errors.append(f"Article start {i} (page {start.get('start_page')}): confidence != 1.0 (got {start.get('confidence')})")

    # Check 5: Boundary ranges count matches article_starts
    if len(boundary_ranges) != len(article_starts):
        errors.append(f"Ranges count != starts count: {len(boundary_ranges)} vs {len(article_starts)}")

    # Check 6: Boundary ranges invariants
    for i, rng in enumerate(boundary_ranges):
        # range.from == article_starts[i].start_page
        if rng["from"] != article_starts[i]["start_page"]:
            errors.append(f"Range {i} ({rng['id']}): from={rng['from']} != start_page={article_starts[i]['start_page']}")

        # Contiguous check (range[i].to + 1 == range[i+1].from)
        if i < len(boundary_ranges) - 1:
            next_rng = boundary_ranges[i + 1]
            if rng["to"] + 1 != next_rng["from"]:
                errors.append(f"Ranges {i} and {i+1} not contiguous: {rng['to']} + 1 != {next_rng['from']}")

        # Last range.to == total_pages
        if i == len(boundary_ranges) - 1:
            if rng["to"] != total_pages:
                errors.append(f"Last range {rng['id']}: to={rng['to']} != total_pages={total_pages}")

    # Check 7: No overlaps
    for i in range(len(boundary_ranges) - 1):
        rng = boundary_ranges[i]
        next_rng = boundary_ranges[i + 1]
        if rng["to"] >= next_rng["from"]:
            errors.append(f"Ranges {i} and {i+1} overlap: {rng['to']} >= {next_rng['from']}")

    return len(errors) == 0, errors


def main():
    # Load stdin (boundaries from BoundaryDetector)
    try:
        raw = json.load(sys.stdin)
        # Unwrap envelope if present
        boundaries = raw if "data" in raw else {"data": raw}
    except json.JSONDecodeError as e:
        print(f"ERROR: Invalid JSON on stdin: {e}", file=sys.stderr)
        sys.exit(1)

    # Load golden artifact
    golden_path = Path(__file__).parent.parent / "golden_tests" / "mg_2025_12_article_starts.json"
    if not golden_path.exists():
        print(f"ERROR: Golden artifact not found: {golden_path}", file=sys.stderr)
        sys.exit(1)

    try:
        with golden_path.open() as f:
            golden_starts = json.load(f)
    except json.JSONDecodeError as e:
        print(f"ERROR: Invalid golden JSON: {e}", file=sys.stderr)
        sys.exit(1)

    # Verify
    success, errors = verify_boundaries(boundaries, golden_starts)

    if success:
        print("✓ All checks passed", file=sys.stderr)
        print(f"✓ {len(boundaries['data']['article_starts'])} article starts verified", file=sys.stderr)
        print(f"✓ {len(boundaries['data']['boundary_ranges'])} boundary ranges verified", file=sys.stderr)
        print(json.dumps({"status": "success", "verified": True}, indent=2))
        sys.exit(0)
    else:
        print("✗ Verification FAILED:", file=sys.stderr)
        for err in errors:
            print(f"  - {err}", file=sys.stderr)
        print(json.dumps({"status": "error", "verified": False, "errors": errors}, indent=2))
        sys.exit(1)


if __name__ == "__main__":
    main()
