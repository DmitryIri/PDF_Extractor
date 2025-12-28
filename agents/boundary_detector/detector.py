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

    for i, a in enumerate(anchors):
        if not isinstance(a, dict):
            raise ValueError(f"anchor[{i}] must be an object")
        if "page" not in a or "type" not in a:
            raise ValueError(f"anchor[{i}] must contain 'page' and 'type'")
        if not isinstance(a["page"], int) or a["page"] < 1 or a["page"] > total_pages:
            raise ValueError(f"anchor[{i}].page must be int within [1..total_pages]")
        if not isinstance(a["type"], str) or not a["type"].strip():
            raise ValueError(f"anchor[{i}].type must be a non-empty string")

    return {
        "issue_id": issue_id,
        "total_pages": total_pages,
        "anchors": anchors,
    }


def _build_pages_model(anchors: list, total_pages: int) -> Dict[int, Dict[str, Any]]:
    pages: Dict[int, Dict[str, Any]] = {}

    for p in range(1, total_pages + 1):
        pages[p] = {
            "page": p,
            "anchors": [],
            "by_type": {"doi": [], "text_block": [], "section_marker": [], "other": []},
            "font_stats": {"max_font_size": None},
            "regions": {"top_40": [], "middle": [], "bottom": []},
        }

    for a in anchors:
        page = a.get("page")
        if page not in pages:
            continue

        pages[page]["anchors"].append(a)

        t = a.get("type")
        if t in pages[page]["by_type"]:
            pages[page]["by_type"][t].append(a)
        else:
            pages[page]["by_type"]["other"].append(a)

        if t == "text_block":
            fs = a.get("font_size")
            if isinstance(fs, (int, float)):
                cur = pages[page]["font_stats"]["max_font_size"]
                if cur is None or fs > cur:
                    pages[page]["font_stats"]["max_font_size"] = fs

    for p in range(1, total_pages + 1):
        pm = pages[p]
        y_vals = []
        for a in pm["anchors"]:
            bb = a.get("bbox")
            if isinstance(bb, list) and len(bb) == 4:
                y0, y1 = bb[1], bb[3]
                if isinstance(y0, (int, float)) and isinstance(y1, (int, float)):
                    y_vals.extend([y0, y1])

        if not y_vals:
            continue

        page_h = max(y_vals)
        top_th = page_h * 0.40
        bot_th = page_h * 0.70

        for a in pm["anchors"]:
            bb = a.get("bbox")
            if not (isinstance(bb, list) and len(bb) == 4):
                continue
            y0, y1 = bb[1], bb[3]
            if not (isinstance(y0, (int, float)) and isinstance(y1, (int, float))):
                continue

            y_mid = (y0 + y1) / 2.0
            if y_mid <= top_th:
                pm["regions"]["top_40"].append(a)
            elif y_mid >= bot_th:
                pm["regions"]["bottom"].append(a)
            else:
                pm["regions"]["middle"].append(a)

    return pages


def main() -> int:
    try:
        payload = _read_stdin_json()
        inp = _validate_input(payload)

        # Stage 1: per-page model is built but not exposed
        _build_pages_model(inp["anchors"], inp["total_pages"])

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
