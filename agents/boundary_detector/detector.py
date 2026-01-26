#!/usr/bin/env python3
"""
BoundaryDetector v1.0.0 - Typography-based Article Start Detection

Implements ArticleStartDetection Policy v_1_0:
- PRIMARY SIGNAL: font_name == "MyriadPro-BoldIt", font_size == 12.0 ± 0.5, len(text) >= 10
- FILTER: RU/EN duplicate detection (consecutive pages)
- BLACKLIST: Known false positives
"""
import json
import os
import re
import sys
from typing import Any, Dict, List, Optional

import policy_v_1_0

COMPONENT = "BoundaryDetector"
VERSION = "1.1.0"  # Added material_kind classification

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
    # Write to fd 1 (stdout) directly
    output = json.dumps(out, ensure_ascii=False) + "\n"
    os.write(1, output.encode('utf-8'))


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
    # Write to fd 1 (stdout) directly
    output = json.dumps(out, ensure_ascii=False) + "\n"
    os.write(1, output.encode('utf-8'))


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


def _has_bilingual_layout_marker(page: int, anchors: List[Dict[str, Any]]) -> bool:
    """
    Check if page has bilingual layout markers suggesting it's a translation
    of the previous page rather than a new article.

    Returns True if page has section markers in English (KEYWORDS, ABSTRACT,
    SUMMARY, INTRODUCTION) indicating structured bilingual content.
    """
    for anchor in anchors:
        if anchor.get("page") == page and anchor.get("type") == "text_block":
            text_upper = anchor.get("text", "").upper()
            if any(marker in text_upper for marker in ["KEYWORDS", "ABSTRACT", "SUMMARY", "INTRODUCTION"]):
                return True
    return False


def _apply_duplicate_filter(candidates: List[Dict[str, Any]], anchors: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """
    Apply RU/EN duplicate filter (narrow rule):
    - Compare first candidate from each unique page
    - If page N is RU-dominant and page N+1 is EN-dominant
    - AND text lengths are similar (within 0.5x to 2.0x range)
    - AND page N+1 has bilingual layout markers (KEYWORDS/ABSTRACT/INTRODUCTION)
    - THEN drop ALL candidates from page N+1 (keep page N)

    The bilingual layout marker check ensures we only filter pages that are
    translations of the previous page (pages 43, 52, 155), not unrelated articles.
    """
    if not POLICY.duplicate_filter_enabled:
        return candidates

    if not candidates:
        return candidates

    # Sort by page for processing
    sorted_cands = sorted(candidates, key=lambda x: x["page"])

    # Track which pages to skip entirely
    skip_pages = set()

    # First pass: identify pages to skip by comparing page representatives
    i = 0
    while i < len(sorted_cands):
        current = sorted_cands[i]
        current_page = current["page"]

        # Skip to next page (skip remaining candidates on current page)
        j = i + 1
        while j < len(sorted_cands) and sorted_cands[j]["page"] == current_page:
            j += 1

        # j now points to first candidate on next page (or end)
        if j < len(sorted_cands):
            next_cand = sorted_cands[j]
            next_page = next_cand["page"]

            # Check if consecutive pages
            if next_page == current_page + 1:
                # Check language dominance on page representatives
                current_ru = _is_cyrillic_dominant(current["text"])
                next_en = _is_latin_dominant(next_cand["text"])

                if current_ru and next_en:
                    # Check length similarity
                    len_current = len(current["text"])
                    len_next = len(next_cand["text"])

                    if len_current > 0 and len_next > 0:
                        ratio = len_next / len_current
                        if 0.5 <= ratio <= 2.0:
                            # Narrow check: only filter if next page has bilingual layout markers
                            if _has_bilingual_layout_marker(next_page, anchors):
                                # Mark next page for skipping
                                skip_pages.add(next_page)

        i = j if j < len(sorted_cands) else len(sorted_cands)

    # Second pass: filter out ALL candidates from skipped pages
    filtered = [c for c in sorted_cands if c["page"] not in skip_pages]

    return filtered


def _has_contents_marker(page: int, anchors: List[Dict[str, Any]], window: int = 2) -> bool:
    """
    Check if page (or nearby pages within window) has a contents_marker anchor.
    Returns True if contents marker detected.
    """
    for anchor in anchors:
        if anchor.get("type") == "contents_marker":
            anchor_page = anchor.get("page")
            if anchor_page and abs(anchor_page - page) <= window:
                return True
    return False


def _has_extractable_authors(page: int, anchors: List[Dict[str, Any]], window: int = 1) -> bool:
    """
    Check if page (or page+window) has ru_authors or en_authors anchors.
    Window allows checking next page for bilingual layout (RU on page N, EN on page N+1).
    Returns True if authors found within window.
    """
    for anchor in anchors:
        anchor_type = anchor.get("type")
        if anchor_type in ("ru_authors", "en_authors"):
            anchor_page = anchor.get("page")
            if anchor_page and page <= anchor_page <= page + window:
                return True
    return False


def _classify_material_kind(page: int, anchors: List[Dict[str, Any]]) -> str:
    """
    Classify material_kind for an article start page.
    Returns: "contents" | "editorial" | "research"

    Rules:
    - contents: page has contents_marker anchor (or nearby within window of 2)
    - editorial: article start WITHOUT extractable authors in window (page..page+1)
    - research: article start WITH extractable authors in window (page..page+1)
    """
    # Check for Contents marker
    if _has_contents_marker(page, anchors, window=2):
        return "contents"

    # Check for authors (research vs editorial)
    if _has_extractable_authors(page, anchors, window=1):
        return "research"
    else:
        return "editorial"


def _detect_article_starts(anchors: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """
    Detect article start pages using typography-based policy.
    Returns list of article start objects with metadata including material_kind.

    Output format: [{start_page: int, confidence: float, signals: dict, material_kind: str}, ...]
    """
    # Step 1: Extract typography candidates (PRIMARY SIGNAL)
    candidates = _extract_typography_candidates(anchors)

    # Step 2: Apply blacklist filter
    candidates = _apply_blacklist_filter(candidates)

    # Step 3: Apply RU/EN duplicate filter
    candidates = _apply_duplicate_filter(candidates, anchors)

    # Step 4: Build article_starts with rich metadata including material_kind
    pages = sorted(set(cand["page"] for cand in candidates))

    article_starts = []
    for page_num in pages:
        material_kind = _classify_material_kind(page_num, anchors)

        article_starts.append({
            "start_page": page_num,
            "confidence": 1.0,  # Typography detection is deterministic (binary match)
            "material_kind": material_kind,
            "signals": {
                "primary": "typography_descriptor",
                "font_name": POLICY.primary_font_name,
                "font_size": POLICY.primary_font_size,
                "tolerance": POLICY.primary_font_size_tolerance,
                "blacklist": list(POLICY.blacklist),
                "ru_en_dedup_policy": "enabled" if POLICY.duplicate_filter_enabled else "disabled",
            }
        })

    return article_starts


def _generate_boundary_ranges(article_starts: List[Dict[str, Any]], total_pages: int) -> List[Dict[str, Any]]:
    """
    Generate boundary ranges from article start objects.
    Each range: {id, from, to, material_kind}
    - id: sequential 1..N (a01, a02, ...)
    - from: start page (inclusive, 1-indexed)
    - to: end page (inclusive, 1-indexed)
    - material_kind: contents | editorial | research
    - Last range ends at total_pages

    Special handling for Contents:
    - If first article is Contents, extend from page 1 to page before next non-contents article
    - This captures multi-page Contents sections (e.g., pages 1-4)
    """
    if not article_starts:
        return []

    # Defensive validation: ensure correct format
    for i, entry in enumerate(article_starts):
        if not isinstance(entry, dict):
            raise ValueError(f"Invalid article_starts[{i}]: expected dict, got {type(entry).__name__}")
        if "start_page" not in entry:
            raise ValueError(f"Invalid article_starts[{i}]: missing 'start_page' field")
        if not isinstance(entry["start_page"], int) or entry["start_page"] < 1:
            raise ValueError(f"Invalid article_starts[{i}]: start_page must be int >= 1, got {entry['start_page']}")
        if "material_kind" not in entry:
            raise ValueError(f"Invalid article_starts[{i}]: missing 'material_kind' field")

    ranges = []

    for i, entry in enumerate(article_starts):
        article_id = i + 1
        from_page = entry["start_page"]
        material_kind = entry["material_kind"]

        # Special handling: Contents range extends from page 1
        if material_kind == "contents" and i == 0:
            from_page = 1  # Contents starts from first page of issue

        # Determine end page
        if i + 1 < len(article_starts):
            # End is the page before next article start
            to_page = article_starts[i + 1]["start_page"] - 1
        else:
            # Last article ends at total_pages
            to_page = total_pages

        ranges.append({
            "id": f"a{article_id:02d}",
            "from": from_page,
            "to": to_page,
            "material_kind": material_kind,
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
