#!/usr/bin/env python3
import json
import sys
from typing import Any, Dict, Optional


import policy_v1
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



# === Stage 2-3: ArticleStartPolicy v1.0 implementation ===
# Source of truth: docs/policies/article_start_policy_v_1_0.md
# Notes:
# - Facts-only deterministic implementation using pages_model from Stage 1.
# - Boosters are computed and reported but are NOT mandatory in v1.0.

from typing import List, Tuple

POL = policy_v1.ARTICLE_START_POLICY_V1


def _is_ru(a: Dict[str, Any]) -> bool:
    return str(a.get("lang", "")).lower() in ("ru", "rus", "russian")


def _is_en(a: Dict[str, Any]) -> bool:
    return str(a.get("lang", "")).lower() in ("en", "eng", "english")


def _has_marker_type(pm: Dict[str, Any], t: str) -> bool:
    # Deterministic: relies on MetadataExtractor producing explicit marker types.
    # If absent, returns False.
    return bool(pm.get("by_type", {}).get(t))


def _detect_ru_title(pm: Dict[str, Any]) -> bool:
    # Policy: RU-title in top_40_percent AND max font on page.
    max_fs = pm.get("font_stats", {}).get("max_font_size")
    if max_fs is None:
        return False

    top = pm.get("regions", {}).get("top_40", [])
    for a in top:
        if not _is_ru(a):
            continue
        if a.get("type") != "text_block":
            continue
        fs = a.get("font_size")
        if isinstance(fs, (int, float)) and fs == max_fs:
            return True
    return False


def _detect_required_ru_blocks(pm0: Dict[str, Any], pm1: Dict[str, Any]) -> Dict[str, bool]:
    # Policy: required blocks may be distributed across first 1–2 pages.
    # We map required blocks to anchor types that must be produced by extractor.
    # Facts-only: if extractor doesn't produce such type, we cannot claim presence.
    mapping = {
        "ru_title": "ru_title",
        "ru_authors": "ru_authors",
        "ru_affiliations": "ru_affiliations",
        "ru_address": "ru_address",
        "ru_abstract": "ru_abstract",
    }

    out: Dict[str, bool] = {}
    for k in POL.required_ru_blocks:
        t = mapping.get(k)
        if not t:
            out[k] = False
            continue
        out[k] = _has_marker_type(pm0, t) or _has_marker_type(pm1, t)
    return out


def _detect_optional_ru(pm0: Dict[str, Any], pm1: Dict[str, Any]) -> Dict[str, bool]:
    mapping = {
        "ru_keywords": "ru_keywords",
        "ru_for_citation": "ru_for_citation",
        "ru_corresponding_author": "ru_corresponding_author",
        "ru_funding": "ru_funding",
        "ru_conflict_of_interest": "ru_conflict_of_interest",
        "ru_received_accepted": "ru_received_accepted",
    }
    out: Dict[str, bool] = {}
    for k in POL.optional_ru_blocks:
        t = mapping.get(k)
        out[k] = bool(t) and (_has_marker_type(pm0, t) or _has_marker_type(pm1, t))
    return out


def _detect_en_block(pm0: Dict[str, Any], pm1: Dict[str, Any]) -> bool:
    # Facts-only: if any of known EN markers exists on page 0/1.
    # Requires extractor to create these marker types.
    en_types = [
        "en_title", "en_authors", "en_affiliations", "en_abstract", "en_keywords",
        "en_for_citation", "en_corresponding_author", "en_funding",
        "en_conflict_of_interest", "en_received_accepted",
    ]
    for t in en_types:
        if _has_marker_type(pm0, t) or _has_marker_type(pm1, t):
            return True
    return False


def _detect_doi_article(pm: Dict[str, Any]) -> Optional[str]:
    for a in pm.get("by_type", {}).get("doi", []):
        txt = str(a.get("text", a.get("value", ""))).strip()
        if POL.doi_article_regex.match(txt):
            return txt
    return None


def detect_article_starts(pages_model: Dict[int, Dict[str, Any]], total_pages: int) -> List[Dict[str, Any]]:
    starts: List[Dict[str, Any]] = []

    for pno in range(1, total_pages + 1):
        pm0 = pages_model[pno]
        pm1 = pages_model.get(pno + 1, {"by_type": {}, "regions": {}, "font_stats": {}})

        ru_title = _detect_ru_title(pm0)
        required = _detect_required_ru_blocks(pm0, pm1)

        if not ru_title:
            continue
        if not all(required.values()):
            continue

        doi = _detect_doi_article(pm0) or _detect_doi_article(pm1)
        opt_ru = _detect_optional_ru(pm0, pm1)
        en_block = _detect_en_block(pm0, pm1)

        signals: Dict[str, Any] = {
            "ru_title": True,
            "ru_authors": bool(required.get("ru_authors")),
            "ru_affiliations": bool(required.get("ru_affiliations")),
            "ru_address": bool(required.get("ru_address")),
            "ru_abstract": bool(required.get("ru_abstract")),
        }
        if doi:
            signals["doi_article"] = doi
        if en_block:
            signals["en_block"] = True

        # Facts-only: policy does not define scoring; fixed confidence for "passed required".
        starts.append({
            "start_page": int(pno),
            "confidence": 0.90,
            "signals": signals,
        })

    return starts
# === end Stage 2-3 ===

def main() -> int:
    try:
        payload = _read_stdin_json()
        inp = _validate_input(payload)

        # Stage 1: per-page model is built but not exposed
        pages_model = _build_pages_model(inp["anchors"], inp["total_pages"])
        data = {
            "issue_id": inp["issue_id"],
            "total_pages": inp["total_pages"],
            "article_starts": detect_article_starts(pages_model, inp["total_pages"]),
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
