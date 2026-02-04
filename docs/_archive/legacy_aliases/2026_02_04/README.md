# Docs Canonicalization — 2026-02-04

Session: docs(canon) audit. All moves below were performed by `git mv` (history-preserving).
No content was modified. No files were silently deleted.

---

## Files moved to archive (superseded → canonical replacement)

| Moved from | Moved to | Canonical replacement |
|-----------|----------|----------------------|
| `docs/design/pdf_extractor_techspec_v_2_5.md` | `docs/_archive/techspec/` | `docs/design/pdf_extractor_techspec_v_2_6.md` |
| `docs/design/pdf_extractor_boundary_detector_v_1_1.md` | `docs/_archive/design/` | `docs/design/pdf_extractor_boundary_detector_v_1_2.md` |
| `docs/state/project_summary_v_2_6.md` | `docs/_archive/summaries/` | `docs/state/project_summary_v_2_11.md` |
| `docs/state/project_summary_v_2_7.md` | `docs/_archive/summaries/` | `docs/state/project_summary_v_2_11.md` |
| `docs/state/project_summary_v_2_8.md` | `docs/_archive/summaries/` | `docs/state/project_summary_v_2_11.md` |
| `docs/state/project_summary_v_2_9.md` | `docs/_archive/summaries/` | `docs/state/project_summary_v_2_11.md` |
| `docs/state/project_summary_v_2_10.md` | `docs/_archive/summaries/` | `docs/state/project_summary_v_2_11.md` |
| `docs/state/REPORT_universal_surname_selection_fix_exec.md` | `docs/_archive/` | `docs/state/execution_report_2026_02_04_universal_surname_selection_fix.md` |

## Duplicate removed

| File | Reason |
|------|--------|
| `docs/_archive/session_logs/session_closure_log_2026_01_12_v1_0.md` | Exact SHA256 duplicate of `docs/state/session_closure_log_2026_01_12_v1_0.md` (pre-sync relic from 2026-01-22 session log sync). Canonical copy in `docs/state/` retained. |

## Pre-existing archive items (no action needed)

These were already in `docs/_archive/` before this session. Noted for completeness:

- `_archive/techspec/pdf_extractor_tech_spec_v_2_3_1.md` — pre-rename techspec
- `_archive/techspec/pdf_extractor_tech_spec_v_2_4.md` — pre-rename techspec v_2_4 (different content from `techspec_v_2_4` below)
- `_archive/techspec/pdf_extractor_techspec_v_2_4.md` — post-rename techspec v_2_4
- `_archive/design/pdf_extractor_boundary_detector_v_1_0.md` — superseded design doc
- `_archive/policies/article_start_policy_v_1_0.md` — pre-rename policy (canonical: `article_start_detection_policy_v_1_0.md`)
- `_archive/policies/boundary_detector_v_1_0.md` — misplaced: is a policy doc, NOT the design doc; different content from `_archive/design/pdf_extractor_boundary_detector_v_1_0.md`
- `_archive/policies/ru_blocks_extraction_policy_v_1_0.md` — legacy policy
- `_archive/plans/pdf_extractor_plan_v_2_2.md`, `v_2_3.md` — superseded plans
- `_archive/contracts/` — legacy contracts (pre-pipeline architecture)
- `_archive/summaries/pdf_extractor_project_summary_v_2_3.md` — pre-Phase-1 summary

## Known immutable-file references (cannot fix, noted)

TechSpec v_2_6 (`docs/design/pdf_extractor_techspec_v_2_6.md`) references `filename_generation_policy_v_1_0.md`. This file is immutable per versioning policy. The reference is historically accurate (v_1_0 was canonical at v_2_6 creation time). Current canonical policy is v_1_1.

BoundaryDetector v_1_2 (`docs/design/pdf_extractor_boundary_detector_v_1_2.md`) likewise references `filename_generation_policy_v_1_0.md` — same situation.

## Session closure log naming inconsistency (noted, no action)

Session closure logs use mixed naming conventions (dots vs underscores in version, tool suffixes like `_Claude` / `_ChatGPT`). These are historical records; renaming would break cross-references in other session logs. Each file is a unique date-scoped artifact, not a version family. No action taken.
