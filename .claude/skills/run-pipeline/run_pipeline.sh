#!/usr/bin/env bash
set -euo pipefail

# /run-pipeline skill entrypoint
# Contract: .claude/skills/run-pipeline/SKILL.md (v_1_0)
# Design source of truth: docs/governance/task_specs/run_pipeline_design_v_1_0.md (v_1_0)
#
# Modes:
#   --execute --issue-id <ID> --journal-code <JC> --pdf-path <P> [--run-id <R>]
#       Full gated run: pre-gate → pipeline → post-gate → audit
#   --pre-gate-only  [--run-id <R>]      Repo health + CORE tests only
#   --post-gate-only --run-dir <RUN_DIR> [--run-id <R>]  Observer validation only
#
# Constraints: no jq, no cp/mv, no new allowlist entries.

usage() {
  cat <<'USAGE'
Usage:
  run_pipeline.sh --execute \
      --issue-id <ID> --journal-code <JC> --pdf-path <P> [--run-id <R>]
    Full gated pipeline run:
      pre-gate (branch + clean tree + export scan + CORE tests)
      → tools/run_issue_pipeline.sh (explicit --run-id, no stdout parsing)
      → post-gate (T=L=E + sha256, observer on outputs/08.json)
      → audit JSON in _audit/claude_code/reports/

  run_pipeline.sh --pre-gate-only [--run-id <R>]
    Repo health + CORE test suite only (no pipeline execution).

  run_pipeline.sh --post-gate-only --run-dir <RUN_DIR> [--run-id <R>]
    Observer validation only (reads existing run artefacts).

Exit codes:
  0  success
  2  usage / pre-gate / input-validation failure
  3  post-gate failure
  N  pipeline exit code forwarded (non-zero, not 0/2/3)
USAGE
}

EXECUTE="0"
PRE_GATE_ONLY="0"
POST_GATE_ONLY="0"
ISSUE_ID=""
JOURNAL_CODE=""
PDF_PATH=""
RUN_ID=""
RUN_DIR=""
RUNS_ROOT="${RUNS_ROOT:-/srv/pdf-extractor/runs}"

while [[ $# -gt 0 ]]; do
  case "$1" in
    --execute)
      EXECUTE="1"; shift 1;;
    --pre-gate-only)
      PRE_GATE_ONLY="1"; shift 1;;
    --post-gate-only)
      POST_GATE_ONLY="1"; shift 1;;
    --issue-id)
      ISSUE_ID="${2:-}"; shift 2;;
    --journal-code)
      JOURNAL_CODE="${2:-}"; shift 2;;
    --pdf-path)
      PDF_PATH="${2:-}"; shift 2;;
    --run-id)
      RUN_ID="${2:-}"; shift 2;;
    --run-dir)
      RUN_DIR="${2:-}"; shift 2;;
    -h|--help)
      usage; exit 0;;
    *)
      echo "Unknown arg: $1" >&2
      usage
      exit 2;;
  esac
done

ts_utc() { date -u +"%Y-%m-%dT%H:%M:%SZ"; }

ensure_audit_dir() {
  mkdir -p _audit/claude_code/reports/
}

audit_path_for() {
  local rid="$1"
  echo "_audit/claude_code/reports/run_pipeline_${rid}.json"
}

# Minimal audit writer (python3; no jq)
write_audit_json() {
  local path="$1"
  local status="$2"
  local message="$3"
  local run_dir="$4"
  local export_path="$5"
  local t_val="$6"
  local l_val="$7"
  local e_val="$8"
  local sha_status="$9"

  python3 - <<PY
import json, os, time
data = {
  "ts_utc": "$(ts_utc)",
  "status": "${status}",
  "message": "${message}",
  "branch": os.popen("git branch --show-current").read().strip(),
  "run_id": "${RUN_ID}",
  "run_dir": "${run_dir}",
  "export_path": "${export_path}",
  "t_total_articles": ${t_val if t_val else "null"},
  "l_articles_len": ${l_val if l_val else "null"},
  "e_pdf_count": ${e_val if e_val else "null"},
  "sha256sum_check": "${sha_status}",
}
os.makedirs(os.path.dirname("${path}"), exist_ok=True)
with open("${path}", "w", encoding="utf-8") as f:
  json.dump(data, f, ensure_ascii=False, indent=2)
PY
}

# JSON extraction helpers (python3; no jq)
json_get_export_path() {
  local json="$1"
  python3 - "$json" <<PY
import json, sys
p=sys.argv[1]
o=json.load(open(p,"r",encoding="utf-8"))
v=(o.get("data") or {}).get("export_path") or ""
print(v)
PY
}

json_get_TL() {
  local json="$1"
  # prints "T L" (two ints) or "0 0" if missing
  python3 - "$json" <<PY
import json, sys
p=sys.argv[1]
o=json.load(open(p,"r",encoding="utf-8"))
data=o.get("data") or {}
t=data.get("total_articles")
arts=data.get("articles") or []
l=len(arts) if isinstance(arts,list) else 0
t = int(t) if isinstance(t,(int,float,str)) and str(t).isdigit() else 0
print(f"{t} {l}")
PY
}

count_export_pdfs() {
  local dir="$1"
  # count PDFs only in top-level of export_path
  find "$dir" -maxdepth 1 -type f -name '*.pdf' | wc -l | tr -d ' '
}

run_sha256_check() {
  local dir="$1"
  ( cd "$dir" && sha256sum -c checksums.sha256 ) >/dev/null 2>&1
}

# Preflight: repo invariants (minimal)
preflight_repo() {
  local branch
  branch="$(git branch --show-current || true)"
  if [[ "$branch" != "main" ]]; then
    echo "Pre-gate failed: branch must be 'main' (got: $branch)" >&2
    return 2
  fi
  if [[ -n "$(git status --porcelain)" ]]; then
    echo "Pre-gate failed: working tree must be clean" >&2
    return 2
  fi
}

# Pre-gate audit writer (python3; no jq).
# Args: path status message steps_json
# steps_json is a single-quoted JSON array string built by the caller.
write_pregate_audit_json() {
  local path="$1"
  local status="$2"
  local message="$3"
  local steps_json="$4"

  python3 - <<PY
import json, os
steps = json.loads('${steps_json}')
data = {
  "ts_utc": "$(ts_utc)",
  "status": "${status}",
  "message": "${message}",
  "branch": os.popen("git branch --show-current").read().strip(),
  "run_id": "${RUN_ID}",
  "mode": "pre-gate-only",
  "steps": steps,
}
os.makedirs(os.path.dirname("${path}"), exist_ok=True)
with open("${path}", "w", encoding="utf-8") as f:
  json.dump(data, f, ensure_ascii=False, indent=2)
PY
}

# Export-artifact scan (known /export patterns only, repo root).
# Returns 0 if clean, 1 if artifacts found.
scan_exports_in_root() {
  local count
  count="$(find . -maxdepth 1 -type f \( \
    -name "conversation-*.txt" \
    -o -name "*-task-*.txt" \
    -o -name "*-claude-code-*.txt" \
    -o -name "20??-??-??-*.txt" \
  \) | wc -l | tr -d ' ')"
  if [[ "$count" -gt 0 ]]; then
    echo "Pre-gate failed: ${count} export artifact(s) in repo root. Run /archive-exports first." >&2
    return 1
  fi
  return 0
}

# CORE test suite runner.
# Discovers and runs the exact set declared by pdf-golden-tests SKILL.md.
# Each step is fail-fast: first failure stops the suite.
# Returns 0 if all pass; 2 on any failure.
# Populates the global STEPS_LOG array with per-step status entries.
declare -a STEPS_LOG=()

run_core_tests() {
  STEPS_LOG=()

  # ── Step C1: pytest unit/ ─────────────────────────────────────────────
  echo "[CORE 1/6] python3 -m pytest tests/unit/ -q …"
  if python3 -m pytest tests/unit/ -q 2>&1; then
    STEPS_LOG+=('{"step":"C1","cmd":"python3 -m pytest tests/unit/ -q","result":"pass"}')
  else
    STEPS_LOG+=('{"step":"C1","cmd":"python3 -m pytest tests/unit/ -q","result":"fail"}')
    echo "[CORE 1/6] FAILED" >&2
    return 2
  fi

  # ── Step C2: material classification golden ──────────────────────────
  echo "[CORE 2/6] bash tests/test_material_classification_golden.sh …"
  if bash tests/test_material_classification_golden.sh 2>&1; then
    STEPS_LOG+=('{"step":"C2","cmd":"bash tests/test_material_classification_golden.sh","result":"pass"}')
  else
    STEPS_LOG+=('{"step":"C2","cmd":"bash tests/test_material_classification_golden.sh","result":"fail"}')
    echo "[CORE 2/6] FAILED" >&2
    return 2
  fi

  # ── Step C3: output builder ───────────────────────────────────────────
  echo "[CORE 3/6] bash tests/test_output_builder.sh …"
  if bash tests/test_output_builder.sh 2>&1; then
    STEPS_LOG+=('{"step":"C3","cmd":"bash tests/test_output_builder.sh","result":"pass"}')
  else
    STEPS_LOG+=('{"step":"C3","cmd":"bash tests/test_output_builder.sh","result":"fail"}')
    echo "[CORE 3/6] FAILED" >&2
    return 2
  fi

  # ── Step C4: output validator integration ────────────────────────────
  echo "[CORE 4/6] bash tests/test_output_validator_integration.sh …"
  if bash tests/test_output_validator_integration.sh 2>&1; then
    STEPS_LOG+=('{"step":"C4","cmd":"bash tests/test_output_validator_integration.sh","result":"pass"}')
  else
    STEPS_LOG+=('{"step":"C4","cmd":"bash tests/test_output_validator_integration.sh","result":"fail"}')
    echo "[CORE 4/6] FAILED" >&2
    return 2
  fi

  # ── Step C5: output validator unit (via pytest; it uses unittest internally) ─
  echo "[CORE 5/6] python3 -m pytest tests/test_output_validator_unit.py -q …"
  if python3 -m pytest tests/test_output_validator_unit.py -q 2>&1; then
    STEPS_LOG+=('{"step":"C5","cmd":"python3 -m pytest tests/test_output_validator_unit.py -q","result":"pass"}')
  else
    STEPS_LOG+=('{"step":"C5","cmd":"python3 -m pytest tests/test_output_validator_unit.py -q","result":"fail"}')
    echo "[CORE 5/6] FAILED" >&2
    return 2
  fi

  # ── Step C6: BoundaryDetector golden regression (data-only) ──────────
  # Preflight: both golden fixtures must exist.
  if [[ ! -f golden_tests/mg_2025_12_boundaries.json ]] || \
     [[ ! -f golden_tests/mg_2025_12_article_starts.json ]]; then
    STEPS_LOG+=('{"step":"C6","cmd":"preflight: golden fixtures","result":"fail","reason":"golden fixtures missing"}')
    echo "[CORE 6/6] FAILED: golden fixtures missing (preflight)" >&2
    return 2
  fi
  echo "[CORE 6/6] cat golden_tests/mg_2025_12_boundaries.json | python3 scripts/verify_boundary_detector_golden.py …"
  if cat golden_tests/mg_2025_12_boundaries.json | python3 scripts/verify_boundary_detector_golden.py 2>&1; then
    STEPS_LOG+=('{"step":"C6","cmd":"cat golden_tests/mg_2025_12_boundaries.json | python3 scripts/verify_boundary_detector_golden.py","result":"pass"}')
  else
    STEPS_LOG+=('{"step":"C6","cmd":"cat golden_tests/mg_2025_12_boundaries.json | python3 scripts/verify_boundary_detector_golden.py","result":"fail"}')
    echo "[CORE 6/6] FAILED" >&2
    return 2
  fi

  return 0
}

# Build a JSON array string from the STEPS_LOG array.
steps_log_to_json() {
  local ifs_save="$IFS"
  IFS=","
  echo "[${STEPS_LOG[*]}]"
  IFS="$ifs_save"
}

pre_gate_only() {
  ensure_audit_dir
  local rid="${RUN_ID:-$(date -u +%Y%m%dT%H%M%SZ)}"
  RUN_ID="${rid}"

  # preflight_repo already ran in main(); if we're here it passed.
  STEPS_LOG=('{"step":"L1","cmd":"branch==main + clean tree","result":"pass"}')

  # Export scan
  echo "[PRE-GATE] scanning for export artifacts in root …"
  if scan_exports_in_root; then
    STEPS_LOG+=('{"step":"L2","cmd":"export artifact scan","result":"pass"}')
  else
    STEPS_LOG+=('{"step":"L2","cmd":"export artifact scan","result":"fail"}')
    local apath
    apath="$(audit_path_for "${rid}")"
    write_pregate_audit_json "${apath}" "fail" "pre-gate: export artifacts in root" "$(steps_log_to_json)"
    echo "Audit: ${apath}" >&2
    return 2
  fi

  # CORE tests
  echo "[PRE-GATE] running CORE test suite …"
  if run_core_tests; then
    echo "[PRE-GATE] CORE suite: all passed"
  else
    local apath
    apath="$(audit_path_for "${rid}")"
    write_pregate_audit_json "${apath}" "fail" "pre-gate: CORE test suite failure" "$(steps_log_to_json)"
    echo "Audit: ${apath}" >&2
    return 2
  fi

  # Success
  local apath
  apath="$(audit_path_for "${rid}")"
  write_pregate_audit_json "${apath}" "ok" "pre-gate-only: all checks passed" "$(steps_log_to_json)"
  echo "Pre-gate OK"
  echo "Audit: ${apath}"
  return 0
}

post_gate_only() {
  # minimal checks: run-dir exists, outputs/08.json exists
  if [[ -z "${RUN_DIR}" ]]; then
    echo "Post-gate failed: missing --run-dir" >&2
    return 3
  fi
  if [[ ! -d "${RUN_DIR}" ]]; then
    echo "Post-gate failed: RUN_DIR is not a directory: ${RUN_DIR}" >&2
    return 3
  fi

  local vjson="${RUN_DIR}/outputs/08.json"
  if [[ ! -f "${vjson}" ]]; then
    echo "Post-gate failed: missing validator envelope: ${vjson}" >&2
    return 3
  fi

  local export_path
  export_path="$(json_get_export_path "${vjson}")"
  if [[ -z "${export_path}" ]]; then
    echo "Post-gate failed: export_path empty in 08.json (.data.export_path)" >&2
    return 3
  fi
  if [[ ! -d "${export_path}" ]]; then
    echo "Post-gate failed: export_path is not a directory: ${export_path}" >&2
    return 3
  fi

  local tl t l e
  tl="$(json_get_TL "${vjson}")"
  t="${tl%% *}"
  l="${tl##* }"
  e="$(count_export_pdfs "${export_path}")"

  if [[ "${t}" -ne "${l}" || "${t}" -ne "${e}" ]]; then
    echo "Post-gate failed: T=L=E violated (T=${t}, L=${l}, E=${e})" >&2
    return 3
  fi

  local sha_status="fail"
  if run_sha256_check "${export_path}"; then
    sha_status="ok"
  else
    echo "Post-gate failed: sha256sum -c checksums.sha256 failed in ${export_path}" >&2
    return 3
  fi

  ensure_audit_dir
  local rid="${RUN_ID:-$(date -u +%Y%m%dT%H%M%SZ)}"
  RUN_ID="${rid}"
  local apath
  apath="$(audit_path_for "${rid}")"
  write_audit_json "${apath}" "ok" "post-gate-only success" "${RUN_DIR}" "${export_path}" "${t}" "${l}" "${e}" "${sha_status}"

  echo "Post-gate OK: T=L=E=${t}, sha256=${sha_status}"
  echo "Audit: ${apath}"
  return 0
}

# Full gated execute: pre-gate → pipeline → post-gate → audit.
# Requires ISSUE_ID, JOURNAL_CODE, PDF_PATH set by caller (main validates).
# Generates or uses RUN_ID; reconstructs RUN_DIR deterministically.
execute_pipeline() {
  # ── Generate RUN_ID if not supplied (match pipeline's own default format) ─
  if [[ -z "${RUN_ID}" ]]; then
    RUN_ID="manual_$(date -u +%Y%m%d_%H%M%S)"
  fi

  ensure_audit_dir

  # ── Pre-gate (reuse existing function; it writes its own audit on fail) ───
  echo "[EXECUTE] running pre-gate …"
  if ! pre_gate_only; then
    echo "[EXECUTE] pre-gate FAILED; pipeline not started." >&2
    exit 2
  fi

  # ── Invoke pipeline (single allowed entrypoint, explicit args) ────────────
  echo "[EXECUTE] launching tools/run_issue_pipeline.sh …"
  echo "  --journal-code  ${JOURNAL_CODE}"
  echo "  --issue-id      ${ISSUE_ID}"
  echo "  --pdf-path      ${PDF_PATH}"
  echo "  --run-id        ${RUN_ID}"

  set +e
  tools/run_issue_pipeline.sh \
    --journal-code  "${JOURNAL_CODE}" \
    --issue-id      "${ISSUE_ID}" \
    --pdf-path      "${PDF_PATH}" \
    --run-id        "${RUN_ID}"
  local pipeline_rc=$?
  set -e

  if [[ ${pipeline_rc} -ne 0 ]]; then
    echo "[EXECUTE] pipeline exited ${pipeline_rc}" >&2
    # Best-effort audit: record failure with known fields, no post-gate values.
    local apath
    apath="$(audit_path_for "${RUN_ID}")"
    write_audit_json "${apath}" "fail" \
      "pipeline exited ${pipeline_rc}" \
      "${RUNS_ROOT}/${ISSUE_ID}_${RUN_ID}" "" "" "" "" "not-run"
    echo "Audit: ${apath}" >&2
    exit ${pipeline_rc}
  fi

  # ── Reconstruct RUN_DIR deterministically (same formula as pipeline) ──────
  RUN_DIR="${RUNS_ROOT}/${ISSUE_ID}_${RUN_ID}"
  echo "[EXECUTE] pipeline OK. RUN_DIR=${RUN_DIR}"

  # ── Post-gate (reuse existing function; RUN_DIR is now set) ───────────────
  echo "[EXECUTE] running post-gate …"
  if ! post_gate_only; then
    echo "[EXECUTE] post-gate FAILED." >&2
    # post_gate_only does not write audit on its own failure path here;
    # write best-effort audit with what we know.
    local apath
    apath="$(audit_path_for "${RUN_ID}")"
    write_audit_json "${apath}" "fail" \
      "post-gate failure after successful pipeline run" \
      "${RUN_DIR}" "" "" "" "" "fail"
    echo "Audit: ${apath}" >&2
    exit 3
  fi

  echo "[EXECUTE] full gated run complete."
}

main() {
  preflight_repo || exit 2

  if [[ "${PRE_GATE_ONLY}" == "1" ]]; then
    pre_gate_only || exit 2
    exit 0
  fi

  if [[ "${POST_GATE_ONLY}" == "1" ]]; then
    post_gate_only || {
      ensure_audit_dir
      local rid="${RUN_ID:-$(date -u +%Y%m%dT%H%M%SZ)}"
      RUN_ID="${rid}"
      local apath
      apath="$(audit_path_for "${rid}")"
      # best-effort audit on failure (values unknown/null)
      write_audit_json "${apath}" "fail" "post-gate-only failure" "${RUN_DIR:-}" "" "" "" "" "fail"
      echo "Audit: ${apath}" >&2
      exit 3
    }
    exit 0
  fi

  # ── Execute mode ──────────────────────────────────────────────────────────
  if [[ "${EXECUTE}" == "1" ]]; then
    # Validate required inputs for pipeline invocation
    local _missing=()
    [[ -z "${ISSUE_ID}"     ]] && _missing+=(--issue-id)
    [[ -z "${JOURNAL_CODE}" ]] && _missing+=(--journal-code)
    [[ -z "${PDF_PATH}"     ]] && _missing+=(--pdf-path)
    if [[ ${#_missing[@]} -gt 0 ]]; then
      echo "Missing required args for --execute: ${_missing[*]}" >&2
      usage
      exit 2
    fi
    execute_pipeline
    exit 0
  fi

  # ── No mode flag: print usage and stop ────────────────────────────────────
  echo "No mode specified. Use --execute, --pre-gate-only, or --post-gate-only." >&2
  usage
  exit 2
}

main "$@"
