#!/usr/bin/env python3
# PDF Extractor — MetadataExtractor
# Canonical deterministic extractor:
# - emits doi anchors (value+bbox)
# - emits text_block anchors (text+lang+bbox+font_size+font_name)
# - emits required RU blocks (ru_title, ru_authors, ru_affiliations, ru_address, ru_abstract)
#   strictly per docs/policies/ru_blocks_extraction_policy_v_1_0.md
#
# v1.2.0: Added font_name to text_block anchors for typography-based BoundaryDetector.
# IMPORTANT: any change to RU block rules must be done by releasing a new policy version.

from __future__ import annotations

import json
import re
import sys
from typing import Any, Dict, List, Optional, Tuple

import fitz  # PyMuPDF


COMPONENT = "MetadataExtractor"
VERSION = "1.2.0"  # Added font_name to text_block anchors for typography-based detection

# Canonical DOI regex (case-insensitive)
DOI_REGEX = re.compile(r"\b10\.\d{4,9}/[-._;()/:A-Z0-9]+\b", re.IGNORECASE)

# Policy regexes (deterministic; must match policy text)
AUTH_INITIALS_RE = re.compile(r"\b[А-ЯЁ]\.\s?[А-ЯЁ]\.", re.IGNORECASE)
AFFILIATIONS_RE = re.compile(r"университет|институт|больниц|центр|кафедр|факультет|академ", re.IGNORECASE)
ADDRESS_RE = re.compile(r"\bг\.\s|ул\.\s|пр\.\s|д\.\s|Россия|РФ|Москва|Санкт-Петербург", re.IGNORECASE)
ABSTRACT_MARKER_RE = re.compile(r"^\s*Аннотация\b[:\s]*", re.IGNORECASE)

# Policy constants
MERGE_FONT_EPS = 0.5
MERGE_Y_GAP = 6.0
TOP_REGION_FRAC = 0.40
RU_REQUIRED_CONFIDENCE = 0.90


def _error_exit(exit_code: int, code: str, message: str, details: Optional[Dict[str, Any]] = None) -> None:
    out = {
        "status": "error",
        "component": COMPONENT,
        "version": VERSION,
        "data": None,
        "error": {"exit_code": exit_code, "code": code, "message": message, "details": details or {}},
    }
    sys.stdout.write(json.dumps(out, ensure_ascii=False) + "\n")
    raise SystemExit(exit_code)


def _detect_lang(text: str) -> str:
    # Deterministic heuristic: presence of Cyrillic => ru, Latin => en, else unknown
    if re.search(r"[А-ЯЁа-яё]", text):
        return "ru"
    if re.search(r"[A-Za-z]", text):
        return "en"
    return "unknown"


def _norm_text(s: str) -> str:
    # Policy: replace multi-spaces to one and strip
    s = re.sub(r"\s+", " ", s or "")
    return s.strip()


def _bbox_from_first_match(page: fitz.Page, needle: str) -> List[float]:
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


def _extract_doi_anchors(doc: fitz.Document) -> List[Dict[str, Any]]:
    anchors: List[Dict[str, Any]] = []
    for page_index in range(doc.page_count):
        page = doc.load_page(page_index)
        text = page.get_text("text") or ""
        for m in DOI_REGEX.finditer(text):
            doi = m.group(0)
            anchors.append(
                {
                    "page": page_index + 1,
                    "type": "doi",
                    "value": doi,
                    "bbox": _bbox_from_first_match(page, doi),
                    "confidence": 0.98,
                }
            )
    return anchors


def _extract_text_blocks(doc: fitz.Document) -> List[Dict[str, Any]]:
    """
    Deterministic text_block anchors from PyMuPDF dict.
    We emit one anchor per span with bbox, font_size, font_name, plus detected lang.
    font_name is required for typography-based article start detection.
    """
    anchors: List[Dict[str, Any]] = []
    for page_index in range(doc.page_count):
        page = doc.load_page(page_index)
        d = page.get_text("dict") or {}
        blocks = d.get("blocks") or []
        for b in blocks:
            if b.get("type") != 0:
                continue
            for line in b.get("lines") or []:
                for span in line.get("spans") or []:
                    text = span.get("text") or ""
                    text_norm = _norm_text(text)
                    if not text_norm:
                        continue
                    bbox = span.get("bbox")
                    if not (isinstance(bbox, (list, tuple)) and len(bbox) == 4):
                        continue
                    fs = span.get("size")
                    if not isinstance(fs, (int, float)):
                        continue
                    # Extract font_name for typography-based detection
                    font_name = span.get("font") or None
                    anchors.append(
                        {
                            "page": page_index + 1,
                            "type": "text_block",
                            "text": text_norm,
                            "lang": _detect_lang(text_norm),
                            "bbox": [float(bbox[0]), float(bbox[1]), float(bbox[2]), float(bbox[3])],
                            "font_size": float(fs),
                            "font_name": font_name,
                            "confidence": 0.90,
                        }
                    )
    return anchors


# ---- RU blocks per docs/policies/ru_blocks_extraction_policy_v_1_0.md ----

def _group_ru_candidates_on_page(text_blocks: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """
    Policy §4: merge neighboring ru text_blocks on same page when:
    - lang == ru for both
    - abs(font_size_1 - font_size_2) <= 0.5
    - abs(y0_next - y1_prev) <= 6.0
    """
    ru = [a for a in text_blocks if a.get("lang") == "ru" and a.get("type") == "text_block"]
    # Sort by y0 then x0 to get deterministic neighbor ordering
    ru.sort(key=lambda x: (float(x["bbox"][1]), float(x["bbox"][0])))

    merged: List[Dict[str, Any]] = []
    for a in ru:
        if not merged:
            merged.append(
                {
                    "page": a["page"],
                    "text": a["text"],
                    "lang": "ru",
                    "bbox": list(a["bbox"]),
                    "font_size": float(a["font_size"]),
                }
            )
            continue

        prev = merged[-1]
        fs1 = float(prev["font_size"])
        fs2 = float(a["font_size"])
        y0_next = float(a["bbox"][1])
        y1_prev = float(prev["bbox"][3])

        if abs(fs1 - fs2) <= MERGE_FONT_EPS and abs(y0_next - y1_prev) <= MERGE_Y_GAP:
            # merge
            prev["text"] = _norm_text(prev["text"] + " " + a["text"])
            prev["bbox"][0] = min(float(prev["bbox"][0]), float(a["bbox"][0]))
            prev["bbox"][1] = min(float(prev["bbox"][1]), float(a["bbox"][1]))
            prev["bbox"][2] = max(float(prev["bbox"][2]), float(a["bbox"][2]))
            prev["bbox"][3] = max(float(prev["bbox"][3]), float(a["bbox"][3]))
            # font_size kept from prev (deterministic; policy doesn't redefine)
        else:
            merged.append(
                {
                    "page": a["page"],
                    "text": a["text"],
                    "lang": "ru",
                    "bbox": list(a["bbox"]),
                    "font_size": float(a["font_size"]),
                }
            )
    return merged


def _pick_ru_title(page_candidates: List[Dict[str, Any]], page_height: float) -> Optional[Dict[str, Any]]:
    # Policy §5
    top_th = page_height * TOP_REGION_FRAC
    eligible = []
    for c in page_candidates:
        y0, y1 = float(c["bbox"][1]), float(c["bbox"][3])
        y_mid = (y0 + y1) / 2.0
        if y_mid <= top_th and len(_norm_text(c["text"])) >= 10:
            eligible.append(c)
    if not eligible:
        return None
    max_fs = max(float(c["font_size"]) for c in eligible)
    # deterministic tie-break: smallest y0, then x0
    best = [c for c in eligible if float(c["font_size"]) == max_fs]
    best.sort(key=lambda x: (float(x["bbox"][1]), float(x["bbox"][0])))
    return best[0]


def _pick_ru_abstract(page_candidates: List[Dict[str, Any]]) -> Optional[Dict[str, Any]]:
    # Policy §6
    for c in page_candidates:
        m = ABSTRACT_MARKER_RE.search(c["text"])
        if m:
            rest = _norm_text(c["text"][m.end():])
            if rest:
                out = dict(c)
                out["text"] = rest
                return out
            # marker found but no content -> still create empty? policy says "includes all after marker";
            # if empty -> do not create.
    return None


def _pick_ru_authors(page_candidates: List[Dict[str, Any]], ru_title: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    # Policy §7: first ru-candidate after title (by y0) matching comma or initials
    y0_title = float(ru_title["bbox"][1])
    after = [c for c in page_candidates if float(c["bbox"][1]) >= y0_title]
    after.sort(key=lambda x: (float(x["bbox"][1]), float(x["bbox"][0])))
    for c in after:
        t = c["text"]
        if len(t) >= 5 and ("," in t or AUTH_INITIALS_RE.search(t)):
            return c
    return None


def _pick_ru_affiliations_and_address(page_candidates: List[Dict[str, Any]], ru_authors: Dict[str, Any]) -> Tuple[Optional[Dict[str, Any]], Optional[Dict[str, Any]]]:
    # Policy §8: scan candidates after authors by y0
    y0_auth = float(ru_authors["bbox"][1])
    after = [c for c in page_candidates if float(c["bbox"][1]) >= y0_auth]
    after.sort(key=lambda x: (float(x["bbox"][1]), float(x["bbox"][0])))

    ru_aff: Optional[Dict[str, Any]] = None
    ru_addr: Optional[Dict[str, Any]] = None

    for c in after:
        if ru_aff is None and AFFILIATIONS_RE.search(c["text"]):
            ru_aff = c
        if ru_addr is None and ADDRESS_RE.search(c["text"]):
            ru_addr = c
        if ru_aff is not None and ru_addr is not None:
            break
    return ru_aff, ru_addr


def _emit_ru_required_anchors(doc: fitz.Document, text_blocks: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    # group text_blocks by page
    by_page: Dict[int, List[Dict[str, Any]]] = {}
    for a in text_blocks:
        if a.get("type") != "text_block":
            continue
        p = int(a["page"])
        by_page.setdefault(p, []).append(a)

    out: List[Dict[str, Any]] = []

    for pno in range(1, doc.page_count + 1):
        page = doc.load_page(pno - 1)
        page_h = float(page.rect.height)
        page_blocks = by_page.get(pno, [])
        if not page_blocks:
            continue

        candidates = _group_ru_candidates_on_page(page_blocks)
        if not candidates:
            continue

        ru_title = _pick_ru_title(candidates, page_h)
        if ru_title:
            out.append(
                {
                    "page": pno,
                    "type": "ru_title",
                    "text": _norm_text(ru_title["text"]),
                    "lang": "ru",
                    "bbox": [float(x) for x in ru_title["bbox"]],
                    "confidence": RU_REQUIRED_CONFIDENCE,
                }
            )

        ru_abstract = _pick_ru_abstract(candidates)
        if ru_abstract:
            out.append(
                {
                    "page": pno,
                    "type": "ru_abstract",
                    "text": _norm_text(ru_abstract["text"]),
                    "lang": "ru",
                    "bbox": [float(x) for x in ru_abstract["bbox"]],
                    "confidence": RU_REQUIRED_CONFIDENCE,
                }
            )

        if ru_title:
            ru_authors = _pick_ru_authors(candidates, ru_title)
            if ru_authors:
                out.append(
                    {
                        "page": pno,
                        "type": "ru_authors",
                        "text": _norm_text(ru_authors["text"]),
                        "lang": "ru",
                        "bbox": [float(x) for x in ru_authors["bbox"]],
                        "confidence": RU_REQUIRED_CONFIDENCE,
                    }
                )
                ru_aff, ru_addr = _pick_ru_affiliations_and_address(candidates, ru_authors)

                if ru_aff:
                    out.append(
                        {
                            "page": pno,
                            "type": "ru_affiliations",
                            "text": _norm_text(ru_aff["text"]),
                            "lang": "ru",
                            "bbox": [float(x) for x in ru_aff["bbox"]],
                            "confidence": RU_REQUIRED_CONFIDENCE,
                        }
                    )

                if ru_addr:
                    out.append(
                        {
                            "page": pno,
                            "type": "ru_address",
                            "text": _norm_text(ru_addr["text"]),
                            "lang": "ru",
                            "bbox": [float(x) for x in ru_addr["bbox"]],
                            "confidence": RU_REQUIRED_CONFIDENCE,
                        }
                    )

    return out


def main() -> None:
    try:
        raw = sys.stdin.read()
        payload = json.loads(raw)
    except Exception as e:
        _error_exit(10, "invalid_input", f"invalid_input: {e}")

    try:
        issue_id = payload["issue_id"]
        pdf_path = payload["pdf"]["path"]
        if not isinstance(issue_id, str) or not issue_id.strip():
            raise ValueError("issue_id must be a non-empty string")
        if not isinstance(pdf_path, str) or not pdf_path.strip():
            raise ValueError("pdf.path must be a non-empty string")
    except Exception as e:
        _error_exit(10, "missing_field", f"missing_field: {e}")

    try:
        doc = fitz.open(pdf_path)
        total_pages = int(doc.page_count)
    except Exception as e:
        _error_exit(20, "extraction_failed", f"extraction_failed: {e}")

    try:
        doi_anchors = _extract_doi_anchors(doc)
        text_blocks = _extract_text_blocks(doc)
        ru_required = _emit_ru_required_anchors(doc, text_blocks)
    except Exception as e:
        _error_exit(20, "anchor_extraction_failed", f"anchor_extraction_failed: {e}", {"exception": str(e)})

    anchors = []
    anchors.extend(doi_anchors)
    anchors.extend(text_blocks)
    anchors.extend(ru_required)

    out = {
        "status": "success",
        "component": COMPONENT,
        "version": VERSION,
        "data": {"issue_id": issue_id, "total_pages": total_pages, "anchors": anchors},
        "error": None,
    }
    sys.stdout.write(json.dumps(out, ensure_ascii=False) + "\n")


if __name__ == "__main__":
    main()
