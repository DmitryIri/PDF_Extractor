# Task Spec — Phase 3: UI/DB Bootstrap

**Version:** v_1_0
**Status:** Bootstrap stub (Plan-only — full plan required in next CC session)
**Date:** 2026-02-04
**Baseline:** Core pipeline complete (8 components) + Universal Surname Selection Fix (Plan-03)

---

## Goal

End-to-end user workflow:
1. User uploads issue PDF via web UI
2. Pipeline runs (8-step, deterministic)
3. User downloads export zip (articles/ + manifest + checksums)

Database layer stores: run metadata, manifests, exported artifacts (addressable by issue + export_id).

---

## Scope

### In scope
- Web UI: upload form (PDF + journal_code + issue_id), run status view, download trigger
- DB: runs table, manifests table, artifacts storage (PDF files)
- Pipeline integration: invoke existing `tools/run_issue_pipeline.sh` from UI backend
- Export packaging: zip of existing export directory structure

### Explicit non-goals (not in Phase 3)
- LLM at runtime (invariant: zero LLM in pipeline)
- n8n orchestration changes (pipeline is already sequential CLI)
- New pipeline components or logic changes
- Multi-user / team features
- Production hardening (rate limits, auth beyond single-user)
- Monitoring / alerting infrastructure

---

## Decision Points (require resolution before full plan)

| # | Decision | Options | Impact |
|---|----------|---------|--------|
| D-P3-1 | Database backend | (a) Supabase (managed Postgres + storage) (b) Local SQLite + filesystem (c) Local Postgres | Architecture, deployment complexity |
| D-P3-2 | Authentication | (a) Single-user / local-only (b) Supabase Auth (email/password) (c) OAuth (Google) | Security, deployment |
| D-P3-3 | Storage backend | (a) Local filesystem (current export layout) (b) Supabase Storage (c) S3-compatible (MinIO) | Cost, operational complexity |
| D-P3-4 | UI framework | (a) Next.js (b) FastAPI + Jinja (c) Flask + Jinja | Dev velocity, deployment |
| D-P3-5 | Pipeline invocation | (a) Subprocess from web backend (b) Task queue (Celery/RQ) (c) Background thread | Concurrency, error handling |

---

## Required Deliverable for Next Session

A **full Plan document** (`task_spec_phase_3_ui_db_plan_v_1_0.md` or equivalent) covering:
- Resolved decision points (D-P3-1 through D-P3-5)
- Component design for UI backend + DB schema
- Integration contract with existing pipeline (stdin/stdout envelope unchanged)
- Testing strategy (UI smoke, DB integration, end-to-end)
- Acceptance criteria

---

## Constraints (inherited from core pipeline)

- Pipeline is deterministic: same input → same output
- Fail-fast: pipeline stops on first error (exit codes)
- T = L = E invariant enforced by OutputValidator
- Export structure immutable: `articles/`, `manifest/export_manifest.json`, `checksums.sha256`, `README.md`
- Runtime artifacts in `/srv/pdf-extractor/` — code in `/opt/projects/pdf-extractor/`
- No business logic in orchestration layer

---

**End of bootstrap stub**
