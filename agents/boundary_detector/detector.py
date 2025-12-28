#!/usr/bin/env python3
import json
import sys
from typing import Any, Dict, Optional


COMPONENT = "BoundaryDetector"
VERSION = "1.0.0"

EXIT_SUCCESS = 0
EXIT_INVALID_INPUT = 10
EXIT_EXTRACTION_FAILED = 20
EXIT_VERIFICATION_FAILED = 30
EXIT_BUILD_FAILED = 40
EXIT_INTERNAL_ERROR = 50


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
    # Минимальная валидация контракта anchors.json (v2.4 / BoundaryDetector v1.0)
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

    # На v1.0 достаточно проверить, что каждый anchor имеет page/type (остальное начнём требовать на шаге 3.2)
    for i, a in enumerate(anchors):
        if not isinstance(a, dict):
            raise ValueError(f"anchor[{i}] must be an object")
        if "page" not in a or "type" not in a:
            raise ValueError(f"anchor[{i}] must contain 'page' and 'type'")
        if not isinstance(a["page"], int) or a["page"] < 1 or a["page"] > total_pages:
            raise ValueError(f"anchor[{i}].page must be int within [1..total_pages]")
        if not isinstance(a["type"], str) or not a["type"].strip():
            raise ValueError(f"anchor[{i}].type must be a non-empty string")

    return {"issue_id": issue_id, "total_pages": total_pages, "anchors": anchors}


def main() -> int:
    try:
        payload = _read_stdin_json()
        inp = _validate_input(payload)

        # v1.0 skeleton: логика детекта будет добавлена на следующих шагах.
        # Пока возвращаем пустой список границ, но envelope и контракты уже корректны.
        data = {
            "issue_id": inp["issue_id"],
            "total_pages": inp["total_pages"],
            "article_starts": [],
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
