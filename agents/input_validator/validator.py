#!/usr/bin/env python3

import sys
import json
from pathlib import Path
from PyPDF2 import PdfReader

COMPONENT = "InputValidator"
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
            error("invalid_input", "Empty stdin", 10)

        payload = json.loads(raw)

        issue_id = payload.get("issue_id")
        journal_code = payload.get("journal_code")
        pdf_path = payload.get("pdf_path")

        if not issue_id or not journal_code or not pdf_path:
            error(
                "invalid_input",
                "Required fields: issue_id, journal_code, pdf_path",
                10
            )

        pdf_file = Path(pdf_path)

        if not pdf_file.exists():
            error(
                "invalid_input",
                f"PDF file does not exist: {pdf_path}",
                10
            )

        if not pdf_file.is_file():
            error(
                "invalid_input",
                f"PDF path is not a file: {pdf_path}",
                10
            )

        reader = PdfReader(str(pdf_file))
        page_count = len(reader.pages)

        result = {
            "status": "success",
            "component": COMPONENT,
            "version": VERSION,
            "data": {
                "issue_id": issue_id,
                "journal_code": journal_code,
                "pdf_path": pdf_path,
                "pages": page_count
            }
        }

        print(json.dumps(result, ensure_ascii=False))
        sys.exit(0)

    except json.JSONDecodeError:
        error("invalid_input", "Input is not valid JSON", 10)
    except Exception as e:
        error("internal_error", str(e), 50)

if __name__ == "__main__":
    main()
