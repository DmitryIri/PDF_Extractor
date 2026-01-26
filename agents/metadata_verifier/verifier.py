#!/usr/bin/env python3
# PDF Extractor — MetadataVerifier
# Verify and enrich article manifest for OutputBuilder readiness.
#
# NEW in v1.1.0: Material-aware enrichment
# - Accepts input from BoundaryDetector (with material_kind) + anchors
# - For research articles: extracts first_author_surname from anchors
#   - Primary source: en_authors (EN preferred)
#   - Fallback source: ru_authors + transliteration
#   - Fail-fast (exit 40) if neither available
# - For contents/editorial/digest: no surname required (service suffixes)
# - Adds first_author_surname_source and evidence fields for research
#
# Contract:
# - stdin: JSON envelope (or raw) with boundary_ranges + anchors
# - stdout (fd1): JSON envelope with VerifiedArticleManifest
# - stderr (fd2): logs only, no JSON
# - exit codes: 0=success, 10=invalid_input, 30=verification_failed, 40=build_failed, 50=internal_error

from __future__ import annotations

import hashlib
import json
import os
import re
import sys
from pathlib import Path
from typing import Any, Dict, List, Optional

COMPONENT = "MetadataVerifier"
VERSION = "1.1.0"  # Material-aware enrichment + surname extraction


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


# Transliteration map (RU → EN, simplified GOST 7.79-2000 System B)
_TRANSLIT_MAP = {
    'А': 'A', 'Б': 'B', 'В': 'V', 'Г': 'G', 'Д': 'D', 'Е': 'E', 'Ё': 'E', 'Ж': 'Zh',
    'З': 'Z', 'И': 'I', 'Й': 'Y', 'К': 'K', 'Л': 'L', 'М': 'M', 'Н': 'N', 'О': 'O',
    'П': 'P', 'Р': 'R', 'С': 'S', 'Т': 'T', 'У': 'U', 'Ф': 'F', 'Х': 'Kh', 'Ц': 'Ts',
    'Ч': 'Ch', 'Ш': 'Sh', 'Щ': 'Shch', 'Ъ': '', 'Ы': 'Y', 'Ь': '', 'Э': 'E', 'Ю': 'Yu', 'Я': 'Ya',
    'а': 'a', 'б': 'b', 'в': 'v', 'г': 'g', 'д': 'd', 'е': 'e', 'ё': 'e', 'ж': 'zh',
    'з': 'z', 'и': 'i', 'й': 'y', 'к': 'k', 'л': 'l', 'м': 'm', 'н': 'n', 'о': 'o',
    'п': 'p', 'р': 'r', 'с': 's', 'т': 't', 'у': 'u', 'ф': 'f', 'х': 'kh', 'ц': 'ts',
    'ч': 'ch', 'ш': 'sh', 'щ': 'shch', 'ъ': '', 'ы': 'y', 'ь': '', 'э': 'e', 'ю': 'yu', 'я': 'ya'
}


def _transliterate_ru_to_en(text: str) -> str:
    """Transliterate Russian text to Latin (simplified GOST 7.79 System B)."""
    result = []
    for char in text:
        result.append(_TRANSLIT_MAP.get(char, char))
    return ''.join(result)


def _extract_first_surname(author_text: str, is_ru: bool = False) -> Optional[str]:
    """
    Extract first surname from author text.

    Expected formats:
    - EN: "Burykina Yu.S., Zharova O.P., ..." → "Burykina"
    - RU: "Бурыкина Ю.С., Жарова О.П., ..." → "Бурыкина"

    Returns first surname (before first comma or space+initials).
    """
    if not author_text:
        return None

    # Split by comma (multiple authors)
    parts = author_text.split(',')
    if not parts:
        return None

    first_author = parts[0].strip()
    if not first_author:
        return None

    # Extract surname (first word before initials)
    # Pattern: "Surname I.I." or "Surname"
    words = first_author.split()
    if not words:
        return None

    surname = words[0].strip()

    # Remove trailing punctuation (dots, commas)
    surname = surname.rstrip('.,;:')

    return surname if surname else None


def _find_anchor_in_window(
    from_page: int,
    to_page: int,
    anchor_type: str,
    anchors: List[Dict[str, Any]]
) -> Optional[Dict[str, Any]]:
    """
    Find first anchor of given type within page window [from_page, to_page].
    Returns anchor dict or None if not found.
    """
    for anchor in anchors:
        if anchor.get("type") == anchor_type:
            anchor_page = anchor.get("page")
            if anchor_page and from_page <= anchor_page <= to_page:
                return anchor
    return None


def _extract_surname_for_research(
    from_page: int,
    anchors: List[Dict[str, Any]]
) -> Dict[str, Any]:
    """
    Extract first_author_surname for research article.

    Returns dict with:
    - first_author_surname: str
    - first_author_surname_source: "en_authors" | "ru_authors_translit"
    - evidence: {anchor_type: str, anchor_page: int}

    Raises SystemExit(40) if neither en_authors nor ru_authors found in window.
    """
    window_end = from_page + 1  # Check page and page+1

    # PRIMARY: Try en_authors first
    en_anchor = _find_anchor_in_window(from_page, window_end, "en_authors", anchors)
    if en_anchor:
        author_text = en_anchor.get("text", "")
        surname = _extract_first_surname(author_text, is_ru=False)
        if surname:
            return {
                "first_author_surname": surname,
                "first_author_surname_source": "en_authors",
                "evidence": {
                    "anchor_type": "en_authors",
                    "anchor_page": en_anchor.get("page")
                }
            }

    # FALLBACK: Try ru_authors + transliteration
    ru_anchor = _find_anchor_in_window(from_page, window_end, "ru_authors", anchors)
    if ru_anchor:
        author_text = ru_anchor.get("text", "")
        surname_ru = _extract_first_surname(author_text, is_ru=True)
        if surname_ru:
            surname_en = _transliterate_ru_to_en(surname_ru)
            return {
                "first_author_surname": surname_en,
                "first_author_surname_source": "ru_authors_translit",
                "evidence": {
                    "anchor_type": "ru_authors",
                    "anchor_page": ru_anchor.get("page")
                }
            }

    # FAIL-FAST: Neither en_authors nor ru_authors found
    _error_exit(
        40,
        "build_failed",
        f"Research article starting at page {from_page}: no en_authors or ru_authors anchor found in window [{from_page}, {window_end}]"
    )


def _verify_and_enrich_boundary_range(
    boundary_range: Dict[str, Any],
    issue_prefix: str,
    anchors: List[Dict[str, Any]],
    splitter_output_dir: Path
) -> Dict[str, Any]:
    """
    Verify and enrich a single boundary range with material-specific enrichment.

    For research articles: extracts first_author_surname from anchors (EN primary, RU fallback)
    For contents/editorial/digest: uses service suffixes (Contents, Editorial, Digest)

    Returns enriched article dict ready for OutputBuilder.
    """
    # Validate required input fields from boundary_range
    required_fields = ["id", "from", "to", "material_kind"]
    for field in required_fields:
        if field not in boundary_range:
            _error_exit(10, "invalid_input", f"Boundary range missing required field '{field}': {boundary_range}")

    article_id = boundary_range["id"]
    from_page = boundary_range["from"]
    to_page = boundary_range["to"]
    material_kind = boundary_range["material_kind"]

    # Validate types
    if not isinstance(from_page, int) or not isinstance(to_page, int):
        _error_exit(10, "invalid_input", f"Article {article_id}: from_page and to_page must be integers")

    if from_page < 1 or to_page < 1:
        _error_exit(30, "verification_failed", f"Article {article_id}: page numbers must be >= 1")

    if from_page > to_page:
        _error_exit(30, "verification_failed", f"Article {article_id}: from_page must be <= to_page")

    if material_kind not in ("contents", "editorial", "research", "digest"):
        _error_exit(10, "invalid_input", f"Article {article_id}: invalid material_kind '{material_kind}'")

    # Format page numbers as 3-digit zero-padded
    from_page_formatted = str(from_page).zfill(3)
    to_page_formatted = str(to_page).zfill(3)

    # Material-specific enrichment
    enriched = {
        "article_id": article_id,
        "from_page": from_page,
        "to_page": to_page,
        "material_kind": material_kind
    }

    # Build expected_filename based on material_kind
    if material_kind == "research":
        # Extract surname from anchors
        surname_data = _extract_surname_for_research(from_page, anchors)
        surname = surname_data["first_author_surname"]
        sanitized_surname = _sanitize_surname(surname)

        if not sanitized_surname:
            _error_exit(40, "build_failed",
                        f"Article {article_id}: first_author_surname '{surname}' is empty after sanitization")

        enriched["first_author_surname"] = sanitized_surname
        enriched["first_author_surname_source"] = surname_data["first_author_surname_source"]
        enriched["evidence"] = surname_data["evidence"]

        expected_filename = f"{issue_prefix}_{from_page_formatted}-{to_page_formatted}_{sanitized_surname}.pdf"

    elif material_kind == "contents":
        expected_filename = f"{issue_prefix}_{from_page_formatted}-{to_page_formatted}_Contents.pdf"

    elif material_kind == "editorial":
        expected_filename = f"{issue_prefix}_{from_page_formatted}-{to_page_formatted}_Editorial.pdf"

    elif material_kind == "digest":
        expected_filename = f"{issue_prefix}_{from_page_formatted}-{to_page_formatted}_Digest.pdf"

    else:
        _error_exit(50, "internal_error", f"Unhandled material_kind: {material_kind}")

    enriched["expected_filename"] = expected_filename

    # Verify splitter output file exists (if splitter_output_dir provided)
    # Expected splitter output path: {splitter_output_dir}/{article_id}.pdf
    if splitter_output_dir:
        splitter_path = splitter_output_dir / f"{article_id}.pdf"

        if not splitter_path.exists():
            _error_exit(30, "verification_failed", f"Article {article_id}: splitter output file does not exist: {splitter_path}")

        if not splitter_path.is_file():
            _error_exit(30, "verification_failed", f"Article {article_id}: splitter output path is not a file: {splitter_path}")

        file_size = splitter_path.stat().st_size
        if file_size == 0:
            _error_exit(30, "verification_failed", f"Article {article_id}: splitter output file has zero size")

        sha256_hash = _compute_sha256(splitter_path)

        enriched["splitter_output"] = {
            "path": str(splitter_path),
            "bytes": file_size,
            "sha256": sha256_hash
        }

    return enriched


def main() -> None:
    # Read stdin
    try:
        raw = json.load(sys.stdin)
    except Exception as e:
        _error_exit(10, "invalid_input", f"Invalid JSON on stdin: {e}")

    # Unwrap envelope (accept output from BoundaryDetector)
    payload = raw.get("data", raw) if isinstance(raw, dict) else raw

    # Validate required top-level fields
    try:
        issue_id = payload.get("issue_id")
        boundary_ranges = payload.get("boundary_ranges")
        anchors = payload.get("anchors")

        if not issue_id:
            raise ValueError("issue_id is required")
        if boundary_ranges is None:
            raise ValueError("boundary_ranges is required")
        if not isinstance(boundary_ranges, list):
            raise ValueError("boundary_ranges must be a list")
        if anchors is None:
            raise ValueError("anchors is required")
        if not isinstance(anchors, list):
            raise ValueError("anchors must be a list")

    except (KeyError, ValueError) as e:
        _error_exit(10, "invalid_input", str(e))

    # Extract issue_prefix from issue_id (e.g., "mg_2025_12" → "Mg_2025-12")
    # For now, use issue_id directly if it matches pattern, or require explicit issue_prefix
    issue_prefix = payload.get("issue_prefix")
    if not issue_prefix:
        # Fallback: try to derive from issue_id (e.g., "mg_2025_12" → "Mg_2025-12")
        # This is a simple heuristic; production should pass issue_prefix explicitly
        parts = issue_id.split('_')
        if len(parts) >= 3:
            journal = parts[0].capitalize()
            year = parts[1]
            month = parts[2]
            issue_prefix = f"{journal}_{year}-{month}"
        else:
            _error_exit(10, "invalid_input", f"Cannot derive issue_prefix from issue_id: {issue_id}")

    # Extract journal_code
    journal_code = _extract_journal_code(issue_prefix)

    # Validate boundary_ranges count > 0
    if len(boundary_ranges) == 0:
        _error_exit(30, "verification_failed", "No boundary_ranges in input (count must be > 0)")

    # Optional: splitter_output_dir (for verifying splitter output files)
    splitter_output_dir_str = payload.get("splitter_output_dir")
    splitter_output_dir = Path(splitter_output_dir_str) if splitter_output_dir_str else None

    # Verify and enrich each boundary range (deterministic order by id)
    ranges_sorted = sorted(boundary_ranges, key=lambda r: r.get("id", ""))

    verified_articles = []
    for boundary_range in ranges_sorted:
        enriched = _verify_and_enrich_boundary_range(
            boundary_range,
            issue_prefix,
            anchors,
            splitter_output_dir
        )
        verified_articles.append(enriched)

    # Determine run_id (if present in payload, use it; otherwise derive from issue_id)
    run_id = payload.get("run_id", f"run_{issue_id}")

    # Build VerifiedArticleManifest
    verified_manifest = {
        "journal_code": journal_code,
        "issue_prefix": issue_prefix,
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
