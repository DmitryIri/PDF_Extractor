#!/usr/bin/env python3
"""
BoundaryDetector v1.0.0 - Typography-based Article Start Detection

Implements ArticleStartDetection Policy v_1_0:
- PRIMARY SIGNAL: font_name == "MyriadPro-BoldIt", font_size == 12.0 ± 0.5, len(text) >= 10
- FILTER: RU/EN duplicate detection (consecutive pages)
- BLACKLIST: Known false positives
"""
import json
import re
import sys
from typing import Any, Dict, List, Optional

import policy_v_1_0

COMPONENT = "BoundaryDetector"
VERSION = "1.0.0"

EXIT_SUCCESS = 0
EXIT_INVALID_INPUT = 10
EXIT_EXTRACTION_FAILED = 20
EXIT_VERIFICATION_FAILED = 30
EXIT_BUILD_FAILED = 40
EXIT_INTERNAL_ERROR = 50

POLICY = policy_v_1_0.ARTICLE_START_DETECTION_POLICY_V1


def _emit_success(data: Dict[str, Any]) -> None:
    out = {
        "status": "success",
        "component": COMPONENT,
        "version": VERSION,
        "data": data,
        "error": None,
    }
    sys.stdout.write(json.dumps(out, ensure_ascii=False) + "\n")


def _emit_error(exit_code: int, error_code: str, message: str, details: Optional[Dict[str, Any]] = None) -> None:
    out = {
        "status": "error",
        "component": COMPONENT,
        "version": VERSION,
        "data": {},
        "error": {
            "exit_code": exit_code,
            "code": error_code,
            "message": message,
            "details": details or {},
        },
    }
    sys.stdout.write(json.dumps(out, ensure_ascii=False) + "\n")


def _read_stdin_json() -> Dict[str, Any]:
    raw = sys.stdin.read()
    if not raw or not raw.strip():
        raise ValueError("stdin is empty")
    return json.loads(raw)


def _validate_input(payload: Dict[str, Any]) -> Dict[str, Any]:
    missing = []
    for k in ("issue_id", "total_pages", "anchors"):
        if k not in payload:
            missing.append(k)
    if missing:
        raise ValueError(f"missing required fields: {', '.join(missing)}")

    issue_id = payload["issue_id"]
    total_pages = payload["total_pages"]
    anchors = payload["anchors"]

    if not isinstance(issue_id, str) or not issue_id.strip():
        raise ValueError("issue_id must be a non-empty string")
    if not isinstance(total_pages, int) or total_pages <= 0:
        raise ValueError("total_pages must be a positive integer")
    if not isinstance(anchors, list):
        raise ValueError("anchors must be an array")

    return {
        "issue_id": issue_id,
        "total_pages": total_pages,
        "anchors": anchors,
    }


def _is_cyrillic_dominant(text: str) -> bool:
    """Deterministic: text is RU if >= 50% of letters are Cyrillic."""
    cyrillic = sum(1 for c in text if '\u0400' <= c <= '\u04FF')
    latin = sum(1 for c in text if ('A' <= c <= 'Z') or ('a' <= c <= 'z'))
    total_letters = cyrillic + latin
    if total_letters == 0:
        return False
    return cyrillic >= total_letters / 2


def _is_latin_dominant(text: str) -> bool:
    """Deterministic: text is EN if >= 50% of letters are Latin."""
    cyrillic = sum(1 for c in text if '\u0400' <= c <= '\u04FF')
    latin = sum(1 for c in text if ('A' <= c <= 'Z') or ('a' <= c <= 'z'))
    total_letters = cyrillic + latin
    if total_letters == 0:
        return False
    return latin >= total_letters / 2


def _matches_blacklist(text: str) -> bool:
    """Case-insensitive blacklist matching."""
    text_lower = text.lower()
    for pattern in POLICY.blacklist:
        if pattern.lower() in text_lower:
            return True
    return False


def _extract_typography_candidates(anchors: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """
    Extract article start candidates based on PRIMARY SIGNAL:
    - font_name == POLICY.primary_font_name
    - font_size in [POLICY.primary_font_size - tolerance, POLICY.primary_font_size + tolerance]
    - len(text) >= POLICY.primary_min_text_length
    """
    candidates = []

    min_size = POLICY.primary_font_size - POLICY.primary_font_size_tolerance
    max_size = POLICY.primary_font_size + POLICY.primary_font_size_tolerance

    for anchor in anchors:
        if anchor.get("type") != "text_block":
            continue

        font_name = anchor.get("font_name")
        if font_name != POLICY.primary_font_name:
            continue

        font_size = anchor.get("font_size")
        if not isinstance(font_size, (int, float)):
            continue
        if not (min_size <= font_size <= max_size):
            continue

        text = anchor.get("text", "")
        if len(text) < POLICY.primary_min_text_length:
            continue

        # Passed PRIMARY SIGNAL
        candidates.append({
            "page": anchor["page"],
            "text": text,
            "font_name": font_name,
            "font_size": font_size,
            "bbox": anchor.get("bbox", [0, 0, 0, 0]),
        })

    return candidates


def _apply_blacklist_filter(candidates: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """Remove candidates matching blacklist patterns."""
    filtered = []
    for cand in candidates:
        if not _matches_blacklist(cand["text"]):
            filtered.append(cand)
    return filtered


def _apply_duplicate_filter(candidates: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """
    Apply RU/EN duplicate filter:
    - If page N is RU-dominant and page N+1 is EN-dominant
    - AND both are consecutive candidates
    - THEN drop page N+1 (keep RU)
    """
    if not POLICY.duplicate_filter_enabled:
        return candidates

    if not candidates:
        return candidates

    # Sort by page for processing
    sorted_cands = sorted(candidates, key=lambda x: x["page"])

    filtered = []
    skip_next = False

    for i in range(len(sorted_cands)):
        if skip_next:
            skip_next = False
            continue

        current = sorted_cands[i]

        # Check if next candidate is consecutive page
        if i + 1 < len(sorted_cands):
            next_cand = sorted_cands[i + 1]

            # Check if consecutive pages
            if next_cand["page"] == current["page"] + 1:
                # Check language dominance
                current_ru = _is_cyrillic_dominant(current["text"])
                next_en = _is_latin_dominant(next_cand["text"])

                if current_ru and next_en:
                    # RU followed by EN duplicate - keep RU, drop EN
                    filtered.append(current)
                    skip_next = True
                    continue

        filtered.append(current)

    return filtered


def _detect_article_starts(anchors: List[Dict[str, Any]]) -> List[int]:
    """
    Detect article start pages using typography-based policy.
    Returns sorted list of unique page numbers.
    """
    # Step 1: Extract typography candidates (PRIMARY SIGNAL)
    candidates = _extract_typography_candidates(anchors)

    # Step 2: Apply blacklist filter
    candidates = _apply_blacklist_filter(candidates)

    # Step 3: Apply RU/EN duplicate filter
    candidates = _apply_duplicate_filter(candidates)

    # Step 4: Extract unique page numbers and sort
    pages = sorted(set(cand["page"] for cand in candidates))

    return pages


def _generate_boundary_ranges(article_starts: List[int], total_pages: int) -> List[Dict[str, Any]]:
    """
    Generate boundary ranges from article start pages.
    Each range: {id, from, to}
    - id: sequential 1..N
    - from: start page (inclusive, 1-indexed)
    - to: end page (inclusive, 1-indexed)
    - Last range ends at total_pages
    """
    if not article_starts:
        return []

    ranges = []

    for i, start in enumerate(article_starts):
        article_id = i + 1
        from_page = start

        # Determine end page
        if i + 1 < len(article_starts):
            # End is the page before next article start
            to_page = article_starts[i + 1] - 1
        else:
            # Last article ends at total_pages
            to_page = total_pages

        ranges.append({
            "id": f"a{article_id:02d}",
            "from": from_page,
            "to": to_page,
        })

    return ranges


def main() -> int:
    try:
        raw = _read_stdin_json()
        payload = raw.get("data", raw) if isinstance(raw, dict) else raw
        inp = _validate_input(payload)

        # Detect article starts
        article_starts = _detect_article_starts(inp["anchors"])

        # Generate boundary ranges
        boundary_ranges = _generate_boundary_ranges(article_starts, inp["total_pages"])

        data = {
            "issue_id": inp["issue_id"],
            "total_pages": inp["total_pages"],
            "article_starts": article_starts,
            "boundary_ranges": boundary_ranges,
        }

        _emit_success(data)
        return EXIT_SUCCESS

    except json.JSONDecodeError as e:
        _emit_error(EXIT_INVALID_INPUT, "invalid_json", "Input is not valid JSON.", {"exception": str(e)})
        return EXIT_INVALID_INPUT

    except ValueError as e:
        _emit_error(EXIT_INVALID_INPUT, "invalid_input", str(e), {})
        return EXIT_INVALID_INPUT

    except Exception as e:
        _emit_error(EXIT_INTERNAL_ERROR, "internal_error", "Unhandled exception.", {"exception": str(e)})
        return EXIT_INTERNAL_ERROR


if __name__ == "__main__":
    sys.exit(main())
