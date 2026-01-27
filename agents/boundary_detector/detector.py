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
VERSION = "1.2.0"  # Fixed Contents/Editorial detection for front matter

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
    pdf_path = payload.get("pdf_path")  # Optional: pass through if present

    if not isinstance(issue_id, str) or not issue_id.strip():
        raise ValueError("issue_id must be a non-empty string")
    if not isinstance(total_pages, int) or total_pages <= 0:
        raise ValueError("total_pages must be a positive integer")
    if not isinstance(anchors, list):
        raise ValueError("anchors must be an array")

    result = {
        "issue_id": issue_id,
        "total_pages": total_pages,
        "anchors": anchors,
    }
    if pdf_path is not None:
        result["pdf_path"] = pdf_path
    return result


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


def _is_editorial_greeting(text: str) -> bool:
    """
    Check if author text is actually an editorial greeting/signature rather than author names.

    Editorial greetings/signatures typically contain:
    - "Уважаемые" (Dear), "С уважением" (Regards)
    - "коллеги" (colleagues), "читатели" (readers)
    - Academic titles: "доктор ... наук", "профессор", "заведующая"
    - Very long text (> 200 chars) with institutional affiliations

    Returns True if text looks like editorial content, not author names.
    """
    if not text:
        return False

    text_lower = text.lower()

    # Strong indicators of editorial greeting/signature
    editorial_markers = [
        "уважаемые",  # Dear
        "с уважением",  # Regards/Sincerely
        "дорогие",    # Dear
        "коллеги",    # colleagues
        "читатели",   # readers
        "авторы и читатели",  # authors and readers
    ]

    for marker in editorial_markers:
        if marker in text_lower:
            return True

    # Editorial signatures with titles and long affiliations
    editorial_titles = [
        "доктор медицинских наук",  # MD/PhD
        "доктор биологических наук",
        "профессор кафедры",  # Professor of Department
        "заведующая лабораторией",  # Head of Laboratory
        "заведующий лабораторией",
        "приглашенный редактор",  # Guest Editor
    ]

    for title in editorial_titles:
        if title in text_lower:
            return True

    # Very long text (> 200 chars) likely editorial signature, not author list
    if len(text) > 200:
        return True

    # Additional check: exclamation at end + addressing words
    if text.strip().endswith("!") and any(word in text_lower for word in ["коллег", "читател", "автор"]):
        return True

    return False


def _has_extractable_authors(page: int, anchors: List[Dict[str, Any]], window: int = 1) -> bool:
    """
    Check if page (or page+window) has ru_authors or en_authors anchors.
    Window allows checking next page for bilingual layout (RU on page N, EN on page N+1).
    Returns True if authors found within window.

    Filters out editorial greetings that are misclassified as ru_authors.
    """
    for anchor in anchors:
        anchor_type = anchor.get("type")
        if anchor_type in ("ru_authors", "en_authors"):
            anchor_page = anchor.get("page")
            if anchor_page and page <= anchor_page <= page + window:
                # Filter out editorial greetings
                if anchor_type == "ru_authors":
                    text = anchor.get("text", "")
                    if _is_editorial_greeting(text):
                        continue  # Skip this anchor, it's not real authors

                return True
    return False


def _classify_material_kind(page: int, anchors: List[Dict[str, Any]]) -> str:
    """
    Classify material_kind for an article start page.
    Returns: "contents" | "editorial" | "research"

    Rules:
    - contents: page has contents_marker anchor (or nearby within window of 2)
    - editorial: article start WITHOUT extractable authors on same page (window=0)
    - research: article start WITH extractable authors in window (page..page+1)

    Editorial detection:
    - Check only the article start page itself (window=0)
    - This prevents misclassifying Editorial when next page has research article authors
    - Example: page 5 (Editorial) followed by page 6 (Research with authors)
    """
    # Check for Contents marker
    if _has_contents_marker(page, anchors, window=2):
        return "contents"

    # Check for authors on article start page only (editorial vs research)
    # Use window=0 to check only the current page, avoiding false positives
    # from subsequent research articles
    if _has_extractable_authors(page, anchors, window=0):
        return "research"
    else:
        return "editorial"


def _detect_contents_on_first_pages(anchors: List[Dict[str, Any]], max_page: int = 4) -> Optional[Dict[str, Any]]:
    """
    Special-case detection for Contents section on first pages (typically pages 1-4).

    Contents sections often lack PRIMARY SIGNAL (MyriadPro-BoldIt typography) but have
    contents_marker anchors. This function checks if any of the first pages (1..max_page)
    have contents_marker, indicating a Contents section.

    Returns article_start dict for Contents if detected, None otherwise.
    """
    for anchor in anchors:
        if anchor.get("type") == "contents_marker":
            anchor_page = anchor.get("page")
            if anchor_page and 1 <= anchor_page <= max_page:
                # Found Contents marker on first pages
                # Use the page where marker was found as start_page
                # (will be adjusted to page 1 by _generate_boundary_ranges)
                return {
                    "start_page": anchor_page,
                    "confidence": 1.0,
                    "material_kind": "contents",
                    "signals": {
                        "primary": "contents_marker_on_first_pages",
                        "detection_method": "special_case_front_matter",
                    }
                }
    return None


def _detect_article_starts(anchors: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """
    Detect article start pages using typography-based policy.
    Returns list of article start objects with metadata including material_kind.

    Output format: [{start_page: int, confidence: float, signals: dict, material_kind: str}, ...]
    """
    article_starts = []

    # Step 0: Special case - detect Contents on first pages (1-4)
    # Contents sections often don't have PRIMARY SIGNAL typography but have contents_marker
    contents_start = _detect_contents_on_first_pages(anchors, max_page=4)
    if contents_start:
        article_starts.append(contents_start)

    # Step 1: Extract typography candidates (PRIMARY SIGNAL)
    candidates = _extract_typography_candidates(anchors)

    # Step 2: Apply blacklist filter
    candidates = _apply_blacklist_filter(candidates)

    # Step 3: Apply RU/EN duplicate filter
    candidates = _apply_duplicate_filter(candidates, anchors)

    # Step 4: Build article_starts with rich metadata including material_kind
    pages = sorted(set(cand["page"] for cand in candidates))

    # Add typography-detected articles (append to existing article_starts list)
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

    # Step 5: Sort by start_page (Contents should be first if detected)
    article_starts.sort(key=lambda x: x["start_page"])

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

        # Pass through pdf_path if present (for downstream components like Splitter)
        if "pdf_path" in inp:
            data["pdf_path"] = inp["pdf_path"]

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
