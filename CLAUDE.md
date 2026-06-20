# CLAUDE.md

Guidance for Claude Code working in this repository.

## Project

**PDF Extractor** — deterministic Python pipeline for extracting articles from scientific journal PDFs. No LLM at runtime; same input always produces same output.

---

## Source of Truth

<!-- Authoritative current versions are in project_files_index.md §2, not here. -->

Read canonical docs before proposing code or architectural changes. `CLAUDE.md` is an entrypoint, not a technical reference.

**Navigation:** `docs/governance/project_files_index.md` — canonical registry with current versions of all docs.

| Doc type | Location | Role |
|---|---|---|
| TechSpec | `docs/design/pdf_extractor_techspec_v_*.md` | Architecture, contracts, exit codes, schemas |
| Plan | `docs/design/pdf_extractor_plan_v_*.md` | Implementation roadmap |
| Project Summary | `docs/state/project_summary_v_*.md` | Current as-is state, component versions |
| Filename Policy | `docs/policies/filename_generation_policy_v_*.md` | Naming rules (MetadataVerifier, OutputBuilder) |
| Article Start Policy | `docs/policies/article_start_detection_policy_v_1_0.md` | BoundaryDetector rules |
| Versioning Policy | `docs/governance/versioning_policy.md` | Immutability, version bumps |

---

## Architecture Invariants (Non-Negotiable)

1. **Python-only** — all computational logic in Python
2. **n8n is orchestrator only** — no business logic in n8n
3. **No LLM at runtime** — LLM only for design/documentation
4. **Determinism** — same input → same output
5. **Fail-fast** — errors via exit code + structured JSON; pipeline stops immediately
6. **T = L = E** — article count in JSON = filenames count = actual PDFs created
7. **Code ≠ Runtime** — code in `/opt/projects/pdf-extractor/`, artifacts in `/srv/pdf-extractor/`
8. **SoT** — canonical docs are SoT; runtime artifacts are NOT
9. **GitHub as Mirror** — `git@github.com:DmitryIri/PDF_Extractor.git`; post-commit hook auto-pushes main

---

## Pipeline

```
InputValidator → PDFInspector → MetadataExtractor → BoundaryDetector →
Splitter → MetadataVerifier → OutputBuilder → OutputValidator
```

Each component: JSON stdin → JSON stdout → stderr logs → deterministic exit code.
Exit codes: 0=success, 10=invalid_input, 20=extraction_failed, 30=verification_failed, 40=build_failed, 50=internal_error.

**Full pipeline run (canonical):**
```bash
tools/run_issue_pipeline.sh \
  --journal-code Mg \
  --issue-id mg_2025_12 \
  --pdf-path /srv/pdf-extractor/inbox/Mg_2025-12.pdf \
  --run-id manual_20260206_120000
```

Or via skill: `/run-pipeline`

---

## Development Environment

- **Code:** `/opt/projects/pdf-extractor/`
- **Runtime:** `/srv/pdf-extractor/`
- **Runtime Python:** `/srv/pdf-extractor/venv/bin/python`
- **Dev venv:** `/opt/projects/pdf-extractor/.venv/`
- **Phase 3 Web UI:** `systemctl status pdf-extractor-ui` → `http://localhost:8080` (SSH tunnel: `ssh -L 18080:localhost:8080 dmitry@2.58.98.101`)
- **Dependencies:** PyMuPDF (fitz), PyPDF2

---

## Testing

**CORE suite** (required before any commit, run via `/run-pipeline` pre-gate or manually):

```bash
pytest tests/unit/ -v
tests/test_material_classification_golden.sh
tests/test_output_builder.sh
tests/test_output_validator_integration.sh
python tests/test_output_validator_unit.py
cat golden_tests/mg_2025_12_boundaries.json | python scripts/verify_boundary_detector_golden.py
```

**Golden fixture:** `mg_2025_12` (29 articles — 1 Contents + 1 Editorial + 27 Research; 100% precision/recall).

---

## Versioning Gate (CRITICAL)

Files matching `*_v_<MAJOR>_<MINOR>.md` are **IMMUTABLE** after commit. Never edit in-place.

To modify: create new version (e.g. `v_2_8` → `v_2_9`), copy content, apply changes, add CHANGELOG entry.

**If uncertain** — STOP and ask before editing any `*_v_*_*.md` file.

---

## Doc Changes (Single Writer Contract)

All changes to `docs/**` go through **Doc-Agent skills only**.

```
/doc-create   — create new versioned doc
/doc-update   — version bump existing doc
/doc-index    — sync project_files_index
/doc-review   — read-only consistency check (no changes)
```

Direct edits to `docs/**` are forbidden except emergency fixes.
Reference: `.claude/rules/single_writer_contract_v_1_0.md`

---

## Session Discipline

- **Start:** `/session-init-pdf_extractor`
- **End:** `/session-close-pdf_extractor`
- **Before commit:** resolve T1 (export artifacts in root → `/archive-exports`) then check CORE suite
- **Context bootstrap:** last `docs/state/session_closure_log_*.md` + `MEMORY.md`

---

## Audit & Safety

- `_audit/` is gitignored — never stage or commit `_audit/**`
- Export artifacts (`*.txt` from `/export`) → archive via `/archive-exports` before session end
- Never modify `_audit/snapshot_*`
- Runtime artifacts stay in `/srv/` — never in `/opt/projects/`
- Check push log: `tools/check_git_push_log.sh`

---

## Skills

| Skill | Purpose |
|---|---|
| `/run-pipeline` | Gated full-pipeline runner (pre-gate → execute → post-gate → audit) |
| `/pdf-golden-tests` | Canonical regression suite (CORE + optional E2E) |
| `/doc-create` | Create new versioned doc |
| `/doc-update` | Version bump existing doc |
| `/doc-review` | Read-only doc consistency checks |
| `/doc-index` | Sync project_files_index |
| `/session-init-pdf_extractor` | Session kickoff |
| `/session-close-pdf_extractor` | Session closure |
| `/archive-exports` | Archive `/export` artifacts (copy → sha256 → verify → confirm delete) |
| `/techspec-plan-sync` | Report TechSpec ↔ Plan inconsistencies |

---

## File Structure

```
agents/           # 8 pipeline components (Python)
docs/             # Canonical documentation (Doc-Agent only)
  design/         # TechSpec, Plan, BoundaryDetector design
  state/          # project_summary, session_closure_logs, history_log
  governance/     # versioning_policy, project_files_index, canonical_artifact_registry
  policies/       # article_start_detection_policy, filename_generation_policy
  portfolio/      # Upwork portfolio assets
golden_tests/     # Golden fixture for mg_2025_12
tests/            # Unit + integration tests, CORE suite scripts
scripts/          # verify_boundary_detector_golden.py, verify_splitter_golden.py
shared/           # author_surname_normalizer.py
tools/            # run_issue_pipeline.sh, check_git_push_log.sh
ui/               # Phase 3 Web UI (FastAPI + HTMX)
.claude/          # Skills, agents, rules, settings
_audit/           # Session artifacts (gitignored, never commit)
```

For full physical paths and doc registry → `docs/governance/project_files_index.md`
