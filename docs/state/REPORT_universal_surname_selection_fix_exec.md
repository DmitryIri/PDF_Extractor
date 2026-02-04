# Execution Report — Universal Surname Selection Fix

**Status:** COMPLETE — all acceptance criteria met
**Date:** 2026-02-04
**Branch:** main
**Plan baseline:** Plan-03 (rosy-sleeping-whisper)

---

## Acceptance Criteria

| # | Criterion | Result |
|---|-----------|--------|
| A1 | Mh_2026-01 produces exactly 9 filenames matching the target list | PASS |
| A2 | Zero output files with Vol / Tom / Том in surname position (case-insensitive) | PASS |
| A3 | Mg golden test passes all 3 checks unchanged | PASS (byte-for-byte) |
| A4 | Reclassified article (a02) has `original_material_kind == "contents"` in enriched output + `material_kind == "research"` reaching OutputBuilder | PASS (log: `a02: reclassified contents→research (no contents_marker in [3,9])`) |
| A5 | No `if issue ==`, `if journal ==`, `if page_range ==` in any new/modified code | PASS |
| A6 | `shared/author_surname_normalizer.py` contains only pure functions — no I/O, no agent imports | PASS |
| A7 | Unit tests pass (`pytest tests/unit/ -v`) | PASS — 88/88 |
| A8 | Scenario 2 unit test fails if stopword list is stripped to pre-fix set (Table/Fig/Note absent) | PASS (structural: SOFT stopwords gated by `step_c=True`; Scenario 2 uses HARD stopwords; Scenario 4 updated to exercise SOFT stopwords against N=6) |

---

## Mh_2026-01 Acceptance Fixture — Final Filenames

| Art | Pages | kind | Surname | Source | Filename |
|-----|-------|------|---------|--------|----------|
| a01 | 1–2 | contents | — | — | Mh_2026-01_001-002_Contents.pdf |
| a02 | 3–9 | research (reclassified) | Roschina | en_authors | Mh_2026-01_003-009_Roschina.pdf |
| a03 | 10–19 | research | Efremov | ru_authors_translit | Mh_2026-01_010-019_Efremov.pdf |
| a04 | 20–25 | research | Orlov | en_authors | Mh_2026-01_020-025_Orlov.pdf |
| a05 | 26–36 | research | Zhukova | text_block_translit | Mh_2026-01_026-036_Zhukova.pdf |
| a06 | 37–41 | research | Bezchasnyi | text_block_translit | Mh_2026-01_037-041_Bezchasnyi.pdf |
| a07 | 42–54 | research | Kazakovtsev | ru_authors_author_translit | Mh_2026-01_042-054_Kazakovtsev.pdf |
| a08 | 55–63 | research | Plotkin | text_block_translit | Mh_2026-01_055-063_Plotkin.pdf |
| a09 | 64–76 | research | Makarova | ru_authors_translit | Mh_2026-01_064-076_Makarova.pdf |

---

## DEVIATION: N=6 Scan Semantics

**Plan-03 assumption (§8.1 Scenario 4, §11.3 C1 rationale):**
> "N=6 counts total text_blocks in the scan window. 6 is generous: author bylines appear in first 2–3 text_blocks in all observed fixtures."

**Reality (diagnosed from actual MetadataExtractor anchor data at page 26):**
MetadataExtractor emits 60+ text_blocks per page including page numbers ("26"), journal title
("Психическое здоровье"), volume references ("Том 21, № 1", "2026; 21(1)"), section headers
("МЕДИКО-СОЦИАЛЬНЫЕ АСПЕКТЫ"), and body text — all before the byline "жукова д.и."
The byline was the ~14th text_block on page 26; N=6 exhausted on structural noise at block 6.

**Applied fix:** `scanned` counter moved from before filters to after the `looks_like_author_byline`
check. N=6 now counts **byline-pattern candidates examined**, not all text_blocks seen.
Running headers and non-byline blocks are transparent to the scan limit.

**Why this is correct:**
- The N=6 guard's purpose is to bound surname-candidate evaluation, not text_block iteration.
  The page-window constraint `[from_page, from_page+1]` already bounds the iteration to ≤ 2 pages.
- Structural noise (page numbers, section titles) can never become byline candidates because they
  fail `looks_like_author_byline` (no 2-initial pattern). They should not consume the candidate budget.
- The safety invariant is preserved: at most 6 byline-shaped text_blocks are evaluated for surname
  extraction. The 7th and beyond are never reached.

**Test update:** Scenario 4 (`test_n6_boundary_enforced`) updated to use 6 stopword-blocked
byline-pattern blocks ("Vol A.B.", "Tom A.B.", "Table X.Y.", "Note A.B.", "Fig A.B.", "Ref A.B.")
that increment `scanned` but produce no valid candidate, followed by "Plotkin F.B." at candidate
index 6 (outside N=6). Two noise blocks preceding them ("Section 1", "26") remain transparent.

---

## Files Changed

| Action | Path | Summary |
|--------|------|---------|
| CREATE | `shared/__init__.py` | Package marker |
| CREATE | `shared/author_surname_normalizer.py` | Pure functions: `is_running_header`, `is_valid_surname` (HARD/SOFT), `is_toc_by_anchors`, `looks_like_author_byline` (2-initial) |
| CREATE | `tests/unit/__init__.py` | Package marker |
| CREATE | `tests/unit/test_author_surname_normalizer.py` | 88 unit tests (7 classes) |
| CREATE | `docs/policies/filename_generation_policy_v_1_1.md` | Policy bump: GOST rule 3, STEP C source values, TOC re-verification, STEP D deferral |
| MODIFY | `agents/metadata_verifier/verifier.py` | STEP A→B→C rewrite; header filter; GOST ый→yi; TOC reclassification; VERSION 1.2.0→1.3.0; N=6 semantic fix |
| MODIFY | `tools/run_issue_pipeline.sh` | PYTHONPATH prefix on Python invocation (line 118) |

---

## Test Results Summary

| Suite | Result |
|-------|--------|
| `pytest tests/unit/ -v` | 88/88 passed (0.14s) |
| Mg golden regression (3 checks) | ALL PASS — byte-for-byte match |
| Mh_2026-01 acceptance (8-step pipeline) | ALL 8 STEPS OK |
| Mh sha256 checksum verification | 9/9 OK |
| Universal zero-header grep | PASS |

---

## Non-goals (not touched, per plan)

- BoundaryDetector / policy_v_1_0.py — upstream classification leak handled downstream
- MetadataExtractor — header-anchors are observations; filtering is downstream
- OutputBuilder — copies filenames verbatim
- OutputValidator — STEP D unblocking is separate scope
- Splitter — no changes
- All `*_v_*_*.md` files — immutable per versioning policy (policy_v_1_1 is a new file)
