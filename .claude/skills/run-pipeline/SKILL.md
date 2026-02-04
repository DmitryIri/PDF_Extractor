---
name: run-pipeline
description: Gated full-pipeline runner — pre-gate (health + golden + clean tree) → execute → post-gate (T=L=E observer + sha256) → audit report. Contract-first; implementation follows after approval.
---

# /run-pipeline — Skill Contract (v_1_0)

**Version:** v_1_0
**Date:** 2026-02-04
**Scope:** Claude Code skill contract for deterministic, DR-aware pipeline runs (contract-first; implementation follows after approval)

## CHANGELOG
- **v_1_0 (2026-02-04):** Initial contract. Must stay aligned with `docs/governance/task_specs/run_pipeline_design_v_1_0.md`.

## 1. Source of truth
This skill MUST implement the design described in:
- `docs/governance/task_specs/run_pipeline_design_v_1_0.md`

If any behavior diverges from that document, the design doc must be version-bumped first.

## 2. Goal
Provide a single, auditable execution wrapper around the PDF Extractor pipeline run:
- Pre-gate: validate repo + prerequisites.
- Execute: delegate only to `tools/run_issue_pipeline.sh`.
- Post-gate: independently validate final artifacts as an observer (T=L=E + sha256).

## 3. Non-goals
- No changes to pipeline implementation.
- No `.claude/settings.json` allowlist changes.
- No UI/Phase 3 scope.
- No writes to repo outside `.claude/skills/run-pipeline/` and `_audit/…` (audit only).

## 4. Trust boundaries
- The pipeline is a participant; gates are observers.
- Post-gate must derive truth from disk artifacts and validator envelope, not banners.

## 5. Hard constraints
- **Do not use `jq`** inside the skill post-gate (jq is not in allowlist). Use `python3 -c` one-liners for JSON reads.
- Do not use `cp`/`mv` in the skill (broad allows were intentionally removed).
- All audit writes must go under `_audit/claude_code/reports/`.

## 6. Inputs and outputs
### Inputs
- An "issue/run request" sufficient for `tools/run_issue_pipeline.sh` (details are defined by the runner script).

### Outputs
- Pipeline-generated runtime artifacts under `/srv/...` (created by the pipeline).
- An audit report created by the skill:
  - `_audit/claude_code/reports/run_pipeline_{run_id}.json`

## 7. Contracted behavior (high-level)
### 7.1 Pre-gate (must fail fast)
- Branch is `main`
- Working tree clean
- Repo health checks and required CORE tests pass (as defined by project policy)
- Input PDF readable and pipeline prerequisites present (pipeline enforces its own preflight too)

### 7.2 Execute (single allowed entrypoint)
- Execute only: `tools/run_issue_pipeline.sh`

### 7.3 Post-gate (observer validation)
- Locate `${RUN_DIR}` from execution context.
- Read validated export path from:
  - `${RUN_DIR}/outputs/08.json` at `.data.export_path`
- Derive:
  - `T` = total_articles (from 08.json, via python3)
  - `L` = len(articles) (from 08.json, via python3)
  - `E` = count of `*.pdf` under final `export_path` (filesystem observer)
- Enforce `T = L = E`
- Run `sha256sum -c checksums.sha256` in `export_path`

### 7.4 Audit
- First line: `mkdir -p _audit/claude_code/reports/`
- Write a JSON report capturing: timestamps, branch, run_id, RUN_DIR, export_path, T/L/E, checksum status, and failure reason if any.

## 8. Implementation notes (deferred)
Implementation files (scripts/entrypoints) are intentionally not created in this step.
They will be added only after this contract is approved.
