#!/usr/bin/env python3

import sys
import json
import fitz  # PyMuPDF


VERSION = "1.0.0"
COMPONENT = "MetadataExtractor"


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

    result = {
        "status": "success",
        "component": COMPONENT,
        "version": VERSION,
        "data": {
            "issue_id": issue_id,
            "total_pages": total_pages,
            "anchors": []
        },
        "error": None
    }

    print(json.dumps(result, ensure_ascii=False))
    sys.exit(0)


if __name__ == "__main__":
    main()
