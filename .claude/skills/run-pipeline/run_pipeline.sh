#!/usr/bin/env bash
set -euo pipefail

# /run-pipeline skill entrypoint (skeleton)
# Contract: .claude/skills/run-pipeline/SKILL.md (v_1_0)
# Design source of truth: docs/governance/task_specs/run_pipeline_design_v_1_0.md (v_1_0)
#
# IMPORTANT:
# - This is a NON-EXECUTING skeleton. It MUST NOT run the pipeline yet.
# - No jq usage. No cp/mv usage. No allowlist changes.
# - It only validates minimal repo invariants and prepares audit dir.

usage() {
  cat <<'USAGE'
Usage:
  run_pipeline.sh --issue <issue_json_or_path> [--run-id <id>]

Notes:
  - This skeleton does NOT execute the pipeline.
  - It only validates minimal repo invariants and prepares audit directory.
USAGE
}

ISSUE=""
RUN_ID=""

while [[ $# -gt 0 ]]; do
  case "$1" in
    --issue)
      ISSUE="${2:-}"; shift 2;;
    --run-id)
      RUN_ID="${2:-}"; shift 2;;
    -h|--help)
      usage; exit 0;;
    *)
      echo "Unknown arg: $1" >&2
      usage
      exit 2;;
  esac
done

if [[ -z "${ISSUE}" ]]; then
  echo "Missing required --issue" >&2
  usage
  exit 2
fi

# Preflight: repo invariants (minimal, fast)
BRANCH="$(git branch --show-current || true)"
if [[ "${BRANCH}" != "main" ]]; then
  echo "Pre-gate failed: branch must be 'main' (got: ${BRANCH})" >&2
  exit 2
fi

if [[ -n "$(git status --porcelain)" ]]; then
  echo "Pre-gate failed: working tree must be clean" >&2
  exit 2
fi

# Audit dir preflight (allowed command surface: mkdir is already allowed)
mkdir -p _audit/claude_code/reports/

# Emit minimal stub audit note (no JSON contract yet; will be added in implementation step)
echo "run-pipeline skeleton: contract is committed, entrypoint stub created."
echo "NOT IMPLEMENTED: pipeline execution is intentionally disabled in this step."
echo "Issue: ${ISSUE}"
echo "Run-ID: ${RUN_ID:-<unset>}"

exit 2
