#!/usr/bin/env python3

import sys
import json
from pathlib import Path
import fitz  # PyMuPDF

COMPONENT = "PDFInspector"
VERSION = "1.0.0"

def error(code, message, exit_code):
    result = {
        "status": "error",
        "component": COMPONENT,
        "version": VERSION,
        "error": {
            "code": code,
            "message": message
        }
    }
    print(json.dumps(result, ensure_ascii=False))
    sys.exit(exit_code)

def main():
    try:
        raw = sys.stdin.read()
        if not raw.strip():
            error("extraction_failed", "Empty stdin", 20)

        payload = json.loads(raw)

        if payload.get("status") != "success":
            error("extraction_failed", "Upstream status is not success", 20)

        data = payload.get("data", {})
        issue_id = data.get("issue_id")
        journal_code = data.get("journal_code")
        pdf_path = data.get("pdf_path")

        if not issue_id or not journal_code or not pdf_path:
            error(
                "extraction_failed",
                "Required fields missing in upstream data",
                20
            )

        pdf_file = Path(pdf_path)
        if not pdf_file.exists() or not pdf_file.is_file():
            error(
                "extraction_failed",
                f"PDF file not accessible: {pdf_path}",
                20
            )

        # Open PDF with PyMuPDF
        doc = fitz.open(str(pdf_file))
        page_count = doc.page_count

        # Basic structural hints (kept minimal by design)
        structure_hints = {
            "has_toc": bool(doc.get_toc()),
            "text_pages": [],
            "blank_pages": []
        }

        # Minimal heuristic: detect empty text pages
        for i in range(page_count):
            page = doc.load_page(i)
            text = page.get_text().strip()
            if not text:
                structure_hints["blank_pages"].append(i + 1)
            else:
                structure_hints["text_pages"].append(i + 1)

        result = {
            "status": "success",
            "component": COMPONENT,
            "version": VERSION,
            "data": {
                "issue_id": issue_id,
                "journal_code": journal_code,
                "pdf_path": pdf_path,
                "pages": page_count,
                "structure_hints": structure_hints
            }
        }

        print(json.dumps(result, ensure_ascii=False))
        sys.exit(0)

    except json.JSONDecodeError:
        error("extraction_failed", "Input is not valid JSON", 20)
    except Exception as e:
        error("internal_error", str(e), 50)

if __name__ == "__main__":
    main()
