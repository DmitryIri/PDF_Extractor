#!/usr/bin/env python3

import sys
import json
import re
import fitz  # PyMuPDF


VERSION = "1.0.2"
COMPONENT = "MetadataExtractor"

# Canonical DOI regex (case-insensitive)
DOI_REGEX = re.compile(
    r'\b10\.\d{4,9}/[-._;()/:A-Z0-9]+\b',
    re.IGNORECASE
)


def error_exit(code, message):
    result = {
        "status": "error",
        "component": COMPONENT,
        "version": VERSION,
        "data": None,
        "error": {
            "code": code,
            "message": message
        }
    }
    print(json.dumps(result, ensure_ascii=False))
    sys.exit(code)


def _bbox_from_first_match(page, needle: str):
    """
    Best-effort bbox for the first occurrence of `needle` on the page.
    If not found, returns a canonical fallback bbox.
    """
    try:
        rects = page.search_for(needle)
        if rects:
            r = rects[0]
            return [float(r.x0), float(r.y0), float(r.x1), float(r.y1)]
    except Exception:
        pass
    return [0.0, 0.0, 0.0, 0.0]


def extract_doi_anchors(doc):
    anchors = []
    for page_index in range(doc.page_count):
        page = doc.load_page(page_index)
        text = page.get_text("text") or ""

        for m in DOI_REGEX.finditer(text):
            doi = m.group(0)
            anchors.append({
                "page": page_index + 1,  # 1-based page numbering (human-readable)
                "type": "doi",
                "value": doi,
                "bbox": _bbox_from_first_match(page, doi),
                "confidence": 0.98
            })

    return anchors


def main():
    try:
        raw_input = sys.stdin.read()
        payload = json.loads(raw_input)
    except Exception as e:
        error_exit(10, f"invalid_input: {e}")

    try:
        issue_id = payload["issue_id"]
        pdf_path = payload["pdf"]["path"]
    except KeyError as e:
        error_exit(10, f"missing_field: {e}")

    try:
        doc = fitz.open(pdf_path)
        total_pages = doc.page_count
    except Exception as e:
        error_exit(20, f"extraction_failed: {e}")

    try:
        anchors = extract_doi_anchors(doc)
    except Exception as e:
        error_exit(20, f"doi_extraction_failed: {e}")

    result = {
        "status": "success",
        "component": COMPONENT,
        "version": VERSION,
        "data": {
            "issue_id": issue_id,
            "total_pages": total_pages,
            "anchors": anchors
        },
        "error": None
    }

    print(json.dumps(result, ensure_ascii=False))
    sys.exit(0)


if __name__ == "__main__":
    main()
