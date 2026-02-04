# run_pipeline_design_v_1_0

**Version:** v_1_0
**Date:** 2026-02-04
**Scope:** Design specification for Claude Code skill `/run-pipeline` (docs-only; no implementation)

## CHANGELOG
- **v_1_0 (2026-02-04):** Initial canonical design. Derived from CC review memos (Iteration 3B context) and grounded repo facts. No code or allowlist changes included.

## 1. Goal
Provide a deterministic, DR-aware, auditable execution wrapper for the PDF Extractor pipeline run:
- Pre-gate validates repo health + required prerequisites before execution.
- Execute uses existing `tools/run_issue_pipeline.sh`.
- Post-gate independently verifies the filesystem outputs (observer posture), confirming T=L=E and checksum integrity.

## 2. Non-goals
- No changes to pipeline implementation.
- No changes to `.claude/settings.json` allowlist.
- No UI/Phase 3 work.
- No long-running commands in this task spec.

## 3. Trust boundaries
- The pipeline is a participant; gates are observers.
- Post-gate must not trust pipeline "success" banners; it must derive truth from artifacts on disk + validator envelope.

## 4. Preconditions (Pre-gate)
Pre-gate MUST stop (fail) if any condition is not met:

### 4.1 Repo health
- `git status` clean (no uncommitted changes).
- Branch is `main`.
- No exports or transient artifacts staged into repo root.
- Core tests pass (at minimum: existing CORE golden tests defined by project policy).

### 4.2 Runtime prerequisites
- Runtime path exists and is writable only by pipeline (skill itself writes only to `_audit/`).
- Input PDF is readable.
- Pipeline prerequisites exist (including `jq` as required by pipeline preflight).

## 5. Execute
Execution is delegated exclusively to:
- `tools/run_issue_pipeline.sh`

No additional execution entrypoints are permitted by this design.

## 6. Artifacts to observe
A run produces a run directory:
- `${RUN_DIR}/outputs/07.json` (OutputBuilder)
- `${RUN_DIR}/outputs/08.json` (OutputValidator envelope)

The design explicitly prefers the **validated** envelope for export location.

## 7. Post-gate (Observer validation)
Post-gate MUST independently validate:

### 7.1 Export path (validated source of truth)
- Extract `export_path` from:
  - `${RUN_DIR}/outputs/08.json` at JSON path `.data.export_path`
- Rationale: OutputValidator envelope is the validated, post-check artifact; reading from it is semantically stronger than reading from builder output.

### 7.2 T = L = E checks (independent)
- `T` = `total_articles` from `${RUN_DIR}/outputs/08.json`
- `L` = count of `articles` array length from `${RUN_DIR}/outputs/08.json`
- `E` = number of generated article PDFs in final `export_path` directory (filesystem observer)

**Important constraint:** do not use `jq` in the skill post-gate (jq not in allowlist). Use `python3 -c` one-liners for JSON extraction.

### 7.3 Checksums
- Verify checksums in final export directory:
  - run `sha256sum -c checksums.sha256` in `export_path`
- This is an observer check independent of pipeline exit banner.

## 8. Audit
- The skill writes an audit report to:
  - `_audit/claude_code/reports/run_pipeline_{run_id}.json`
- The audit step MUST begin with:
  - `mkdir -p _audit/claude_code/reports/`
- The report captures: timestamps, inputs, branch, run_id, derived T/L/E, export_path, checksum status, and any failure reason.

## 9. Minimal canonical patch list (accepted changes)
1) Export path source: use `outputs/08.json` + `.data.export_path` + explicit rationale (validated envelope).
2) Replace jq in post-gate with `python3 -c` one-liners (no allowlist expansion).
3) Add `mkdir -p _audit/claude_code/reports/` as explicit preflight in audit step.
4) Governance placement: `docs/governance/task_specs/run_pipeline_design_v_1_0.md` (aligned with repo conventions).

## 10. Alternatives (grounded; limited)
### 10.1 Skip post-gate, trust pipeline exit code
- For: OutputValidator already enforces T=L=E and checksum logic.
- Against: post-gate is the only observer that re-checks the final filesystem state at the export_path boundary. Keep post-gate.

### 10.2 Run E2E golden as part of post-gate
- For: validates produced PDFs on disk.
- Against: current test script hardcodes `/tmp/out.json`; pipeline writes Splitter output to `${RUN_DIR}/outputs/05.json`. Wiring would require script changes or copying (cp is prompt-gated). Prefer direct observer checks (T=L=E + sha256).
