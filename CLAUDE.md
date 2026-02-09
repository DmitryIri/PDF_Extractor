# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

PDF Extractor is a deterministic multi-agent pipeline for extracting individual articles from PDF issues of scientific journals. The project follows a production-first approach with DR architecture.

**Primary documentation:** `docs/design/pdf_extractor_techspec_v_2_6.md` (canonical, self-contained)

## Architecture Invariants (Non-Negotiable)

1. **Python-only** — all computational logic in Python
2. **n8n is orchestrator only** — no business logic in n8n
3. **No LLM at runtime** — LLM only for design/documentation
4. **Determinism** — same input → same output
5. **Fail-fast** — errors via exit code + structured JSON; pipeline stops immediately
6. **T = L = E invariant** — article count in JSON = file names count = actual PDF files created
7. **Code ≠ Runtime** — code in `/opt/projects/pdf-extractor/`, runtime artifacts in `/srv/pdf-extractor/`
8. **Single Source of Truth (SoT)** — code and documentation in repo are SoT; runtime artifacts are NOT SoT
9. **GitHub as Mirror** — GitHub (`git@github.com:DmitryIri/PDF_Extractor.git`) is a mirror remote of SoT on Server_Latvia; primary development and deployment occur on the server; post-commit hook automatically pushes main branch to GitHub

## Pipeline Components (Sequential Execution)

```
InputValidator → PDFInspector → MetadataExtractor → BoundaryDetector → Splitter → MetadataVerifier → OutputBuilder → OutputValidator
```

Each component:
- Reads JSON from stdin, writes JSON to stdout, logs to stderr
- Returns structured envelope: `{status, component, version, data, error}`
- Uses exit codes: 0=success, 10=invalid_input, 20=extraction_failed, 30=verification_failed, 40=build_failed, 50=internal_error

**All components implemented and tested (Phase 2 complete).**

## Key Components

### MetadataExtractor (`agents/metadata_extractor/extractor.py`)
- Extracts raw anchors (DOI, text_block, ru_title, ru_authors, etc.) from PDF
- **Does NOT apply policy** — outputs observations only, no interpretation
- Uses PyMuPDF (fitz) for PDF parsing

### BoundaryDetector (`agents/boundary_detector/detector.py`)
- Core component that determines article boundaries from anchors
- **Single carrier of ArticleStartPolicy** — applies `policy_v_1_0.py`
- DOI alone is NEVER sufficient for article start detection
- Requires all 5 RU blocks: ru_title, ru_authors, ru_affiliations, ru_address, ru_abstract
- Policy documentation: `docs/policies/article_start_detection_policy_v_1_0.md`

### InputValidator / PDFInspector
- Validation and structural inspection of input PDF
- Uses PyPDF2 and PyMuPDF respectively

### Splitter (`agents/splitter/splitter.py`)
- Physical PDF splitting by boundary ranges from BoundaryDetector
- Uses PyMuPDF for page extraction
- Creates individual article PDFs in output directory
- Deterministic output (SHA256 stable across runs)

### MetadataVerifier (`agents/metadata_verifier/verifier.py`)
- Validates manifest from BoundaryDetector
- Enriches with journal_code, issue_prefix, expected_filename
- Extracts first_author_surname (STEP A→B→C algorithm)
- Policy: `docs/policies/filename_generation_policy_v_1_1.md`
- TOC re-verification: checks contents_marker in article's own page range

### OutputBuilder (`agents/output_builder/builder.py`)
- Assembles final export directory structure
- Export layout:
  - `articles/` — article PDFs with canonical naming
  - `manifest/export_manifest.json` — export metadata
  - `checksums.sha256` — SHA256 checksums (SHA256SUMS format)
  - `README.md` — human-readable instructions
- Atomic write: builds in `.tmp/` → atomic rename
- Naming rule: `{IssuePrefix}_{PPP-PPP}_{FirstAuthorSurname}.pdf`

### OutputValidator (`agents/output_validator/validator.py`)
- Final validation of T=L=E invariant
- Verifies checksums (sha256)
- Validates filename patterns
- Exit 30 (verification_failed) on any mismatch

## Running Components

### Individual components
Components are standalone Python scripts reading from stdin:

```bash
# InputValidator
echo '{"issue_id": "mg_2025_12", "journal_code": "mg", "pdf_path": "/path/to/file.pdf"}' | python agents/input_validator/validator.py

# MetadataExtractor
echo '{"issue_id": "mg_2025_12", "pdf": {"path": "/path/to/file.pdf"}}' | python agents/metadata_extractor/extractor.py

# BoundaryDetector (requires anchors JSON)
cat anchors.json | python agents/boundary_detector/detector.py

# Splitter (requires boundaries JSON)
cat boundaries.json | python agents/splitter/splitter.py

# MetadataVerifier (requires splitter output + anchors)
cat splitter_output.json | python agents/metadata_verifier/verifier.py

# OutputBuilder (requires verified manifest)
cat verified_manifest.json | python agents/output_builder/builder.py

# OutputValidator (requires builder output)
cat builder_output.json | python agents/output_validator/validator.py
```

### Full pipeline run
Use the canonical entrypoint:

```bash
tools/run_issue_pipeline.sh \
  --journal-code Mg \
  --issue-id mg_2025_12 \
  --pdf-path /srv/pdf-extractor/tmp/Mg_2025-12.pdf \
  --run-id manual_20260206_120000
```

**Or via Claude Code skill** (recommended):
```
/run-pipeline
```

**Runtime environment:**
- Runtime venv: `/srv/pdf-extractor/venv/`
- Python: `/srv/pdf-extractor/venv/bin/python`
- Run outputs: `/srv/pdf-extractor/runs/${ISSUE_ID}_${RUN_ID}/`

## Dependencies

- Python 3.12+
- PyMuPDF (fitz) — PDF text/layout extraction
- PyPDF2 — PDF validation

**Virtual environments:**
- Code venv (development): `/opt/projects/pdf-extractor/.venv/`
- Runtime venv (execution): `/srv/pdf-extractor/venv/`

**Runtime Python:** Use `/srv/pdf-extractor/venv/bin/python` for pipeline execution.

## Audit & DR Principles

**Audit locations:**
- `_audit/claude_code/exports/` — archived /export artifacts (session-specific)
- `_audit/claude_code/reports/` — execution reports, sha256 manifests
- `_audit/reference_inputs/` — manual golden reference artifacts
- `_audit/snapshot_*/` — repo snapshots (do not modify)

**DR safety rules:**
- NEVER git-add or commit anything under `_audit/**` (gitignored)
- NEVER modify `_audit/snapshot_*` folders
- All runtime artifacts in `/srv/pdf-extractor/` (NOT in `/opt/projects/`)
- Export artifacts from Claude Code `/export` → archive via `/archive-exports` skill

**Session artifacts lifecycle:**
1. Claude Code `/export` → repo root (*.txt files)
2. `/archive-exports` → `_audit/claude_code/exports/${SESSION_ID}/`
3. SHA256 manifest → `_audit/claude_code/reports/sha256_exports_${SESSION_ID}.txt`
4. User confirms deletion of root files

## Git & GitHub Workflow

**Remote configuration:**
- Origin: `git@github.com:DmitryIri/PDF_Extractor.git` (mirror)
- SoT: `/opt/projects/pdf-extractor/` on Server_Latvia

**Auto-push mechanism:**
- Git post-commit hook (`.git/hooks/post-commit`) automatically pushes `main` branch to GitHub
- Hook runs in background — does not block commits on network errors
- Hook skips push if commit modifies `_audit/**` files (safety check)
- Push logs: `/tmp/git-auto-push.log`

**Check push status:**
```bash
tools/check_git_push_log.sh
```

**Manual push:**
If auto-push fails or you need to push other branches:
```bash
git push origin <branch-name>
```

**Safety:**
- `_audit/**` is gitignored and never pushed
- Hook checks for audit files before push (defense in depth)
- Network failures do not block local commits

## File Layout

```
agents/           # Pipeline components (Python) — all 8 components
  input_validator/
  pdf_inspector/
  metadata_extractor/
  boundary_detector/
  splitter/
  metadata_verifier/
  output_builder/
  output_validator/
docs/             # Canonical documentation
  governance/     # Meta-documents (protocols, policies index, task_specs)
  state/          # Project state (summaries, session logs)
  design/         # TechSpec, Plan, component designs
  policies/       # Versioned policy documents
  _archive/       # Archived non-canonical versions
tests/            # Unit and golden tests
  unit/           # Pytest unit tests
  fixtures/       # Test input fixtures (JSON)
  manual/         # E2E manual tests
  test_*.sh       # CORE test suite scripts
scripts/          # Verification scripts
  verify_boundary_detector_golden.py
  verify_splitter_golden.py
golden_tests/     # Golden test fixtures (mg_2025_12)
shared/           # Shared utilities
  author_surname_normalizer.py
tools/            # Operational tooling
  run_issue_pipeline.sh  # Canonical full-pipeline entrypoint
.claude/          # Claude Code configuration
  skills/         # User-invocable skills
  rules/          # Ops routing rules
  settings.json   # Project-level permissions
_audit/           # Audit artifacts (gitignored, never commit)
  claude_code/    # Claude Code session artifacts
  reference_inputs/  # Manual golden references
  snapshot_*/     # Repo snapshots (do not modify)
```

## Testing

**Test structure:**
```
tests/
  unit/                          # Pytest unit tests
    test_author_surname_normalizer.py
  test_material_classification_golden.sh
  test_output_builder.sh
  test_output_validator_integration.sh
  test_output_validator_unit.py
  fixtures/                      # Test input fixtures (JSON)
  manual/                        # E2E manual tests
    test_full_pipeline_mg_2025_12.sh
```

**CORE test suite** (used by run-pipeline pre-gate):
1. `pytest tests/unit/ -v` — unit tests
2. `tests/test_material_classification_golden.sh` — material classification
3. `tests/test_output_builder.sh` — builder validation
4. `tests/test_output_validator_integration.sh` — validator integration
5. `tests/test_output_validator_unit.py` — validator unit tests
6. BoundaryDetector golden: `cat golden_tests/mg_2025_12_boundaries.json | python scripts/verify_boundary_detector_golden.py`

**Golden test fixtures:**
- Issue: `mg_2025_12` (29 articles: 1 Contents + 1 Editorial + 27 Research)
- Anchors: `golden_tests/mg_2025_12_anchors.json` (18,184 anchors)
- Boundaries: `golden_tests/mg_2025_12_boundaries.json` (28 article_starts)
- Splitter output: `golden_tests/mg_2025_12_splitter_output.json`

**Test verification scripts:**
- `scripts/verify_boundary_detector_golden.py` — validates article_starts, confidence, boundary_ranges
- `scripts/verify_splitter_golden.py` — validates PDFs vs boundary ranges

## Contract Schemas

### Anchors (MetadataExtractor → BoundaryDetector)
```json
{"issue_id": "...", "total_pages": N, "anchors": [{page, type, value/text, bbox, confidence, ...}]}
```

### Article starts (BoundaryDetector output)
```json
{"status": "success", "data": {"article_starts": [{start_page, confidence, signals: {...}, material_kind}]}}
```

### Boundaries (BoundaryDetector → Splitter)
```json
{"status": "success", "data": {"boundaries": [{from_page, to_page, material_kind, article_index}]}}
```

### Verified manifest (MetadataVerifier → OutputBuilder)
```json
{
  "status": "success",
  "data": {
    "articles": [{
      "article_index": 0,
      "from_page": 5, "to_page": 5,
      "material_kind": "editorial",
      "expected_filename": "Mg_2025-12_005-005_Editorial.pdf",
      "splitter_output": {"sha256": "...", "bytes": ...}
    }]
  }
}
```

### Export (OutputBuilder → OutputValidator)
```json
{
  "status": "success",
  "data": {
    "export_path": "/srv/pdf-extractor/exports/...",
    "total_articles": 29,
    "articles": [{filename, sha256, bytes, from_page, to_page}]
  }
}
```

## Policy Versioning

Policies are versioned and canonical. Changes require new version release (e.g., v_1_0 → v_1_1):

### Active Policies
- **Article Start Detection Policy v_1_0** — `docs/policies/article_start_detection_policy_v_1_0.md`
  - Code: `agents/boundary_detector/policy_v_1_0.py`
  - Applied by: BoundaryDetector
  - DOI alone is NEVER sufficient; requires all 5 RU blocks

- **Filename Generation Policy v_1_1** — `docs/policies/filename_generation_policy_v_1_1.md`
  - Applied by: MetadataVerifier, OutputBuilder
  - GOST 7.79-2000 System B transliteration (rules 1-3)
  - STEP A→B→C surname extraction (incl. text_block fallback)
  - TOC re-verification, gene symbol validation
  - Supersedes: v_1_0 (2026-02-04)

## Milestones & Accepted Decisions

### Phase 2: Core Pipeline — ✅ COMPLETED (2026-02-06)
All 8 pipeline components implemented and tested:
- ✅ InputValidator
- ✅ PDFInspector
- ✅ MetadataExtractor (v_1_0.1)
- ✅ BoundaryDetector (v_1_2)
- ✅ Splitter
- ✅ MetadataVerifier (v_1_3_0)
- ✅ OutputBuilder (v_1_1_0)
- ✅ OutputValidator

**Evidence:**
- Golden test: `mg_2025_12` (29 articles, 100% precision/recall)
- All CORE tests: PASS
- Universal Surname Selection Fix: PASS (Mh_2026-01, 9 articles)

### Mg_2026-01 Production Validation — ✅ COMPLETED (2026-02-06)
First production issue processing after golden test validation:
- Issue: Mg_2026-01 (8 articles: 1 Contents + 1 Editorial + 6 Research)
- Pipeline: Full E2E run via run-pipeline skill
- Result: T=L=E=8, sha256 verified
- Export: `/srv/pdf-extractor/exports/Mg/2026/Mg_2026-01/exports/2026_02_06__19_12_02/`

**Grenaderova bugfix** (commit 55e0f08):
- Issue: Multi-line RU title (4 candidates) vs EN title (2 candidates) caused false split
- Fix: BoundaryDetector dedup ratio — sum all candidates per page (not just first)
- Impact: Pages 27-36 now single file (was incorrectly split into 2)
- Validation: Regression check confirmed only Grenaderova changed (7 other files unchanged)

### run-pipeline Skill — ✅ ACCEPTED (AC1-AC7, 2026-02-06)
Full acceptance testing completed (pre-gate → execute → post-gate → audit):
- AC1 (pre-gate-only): PASS — CORE suite green
- AC2 (execute E2E): PASS — T=L=E=29, sha256 OK
- AC3 (post-gate observer): PASS — audit created
- AC4-AC6 (failure scenarios): PASS — DR-safe protocol
- AC7 (audit coverage): PASS — required fields present

**Evidence:**
- Execution report: `_audit/claude_code/reports/execution_report_run_pipeline_ac1_ac7_2026_02_06.md`
- Audit artifacts: `_audit/claude_code/reports/run_pipeline_ac*.json` (13 files)

### Accepted Policies
- **Article Start Detection Policy v_1_0** — BoundaryDetector rules
- **Filename Generation Policy v_1_1** — MetadataVerifier/OutputBuilder rules
  - GOST 7.79-2000 System B transliteration
  - STEP A→B→C surname extraction (incl. text_block fallback)
  - TOC re-verification, gene symbol validation

## Skills & Toolbelt

**Расположение:** `.claude/skills/` и `.claude/rules/`

### Available Skills (via Skill tool)
- **run-pipeline** — gated full-pipeline runner (pre-gate → execute → post-gate)
  - Contract: `docs/governance/task_specs/run_pipeline_design_v_1_0.md`
  - Status: ✅ Accepted (AC1-AC7 PASS, 2026-02-06)
  - Evidence: `_audit/claude_code/reports/execution_report_run_pipeline_ac1_ac7_2026_02_06.md`
- **pdf-golden-tests** — canonical regression suite (CORE + optional E2E)
- **techspec-plan-sync** — report TechSpec↔Plan inconsistencies
- **keybindings-help** — keybinding customization

### Archive-Exports Mechanism
- **archive-exports** — canonical mechanism for archiving /export artifacts
  - Located in: `.claude/skills/archive-exports/`
  - Workflow: copy → sha256 → verify → user-confirm delete
  - Used by: session-close skill, manual invocation per ops_router rules

### Rules (Ops Router)
- **ops_router_v_1_1.md** — automatic skill routing & reminders
  - T1: root export artifacts → propose /archive-exports
  - T3: before commit → check T1, never stage `_audit/**`
- **audit_exports.md** — canonical policy for /export artifacts archival

## Versioning Gate (CRITICAL)

**Rule:** Files with semantic version suffix pattern `*_v_<MAJOR>_<MINOR>.md` are **IMMUTABLE**.

**Examples:**
- `project_summary_v_2_6.md` — immutable
- `techspec_v_2_5.md` — immutable
- `policy_v_1_0.md` — immutable

**To modify a versioned file:**
1. **NEVER edit the existing file in-place**
2. Create a new file with bumped version (e.g., `v_2_6` → `v_2_7`)
3. Copy content from old version
4. Apply changes to the new version
5. Update version header and add CHANGELOG entry

**If uncertain:** STOP and ask for confirmation before editing any file matching `*_v_*_*.md`.

**Reference:** `docs/governance/versioning_policy.md` v_2_0, §1, Rule 3
