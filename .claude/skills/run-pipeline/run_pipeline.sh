#!/usr/bin/env bash
set -euo pipefail

# /run-pipeline skill entrypoint
# Contract: .claude/skills/run-pipeline/SKILL.md (v_1_0)
# Design source of truth: docs/governance/task_specs/run_pipeline_design_v_1_0.md (v_1_0)
#
# IMPORTANT:
# - This entrypoint STILL DOES NOT execute the pipeline.
# - Adds observer-only post-gate mode: --post-gate-only --run-dir <RUN_DIR>
# - No jq usage. No cp/mv usage. No allowlist changes.

usage() {
  cat <<'USAGE'
Usage:
  run_pipeline.sh --issue <issue_json_or_path> [--run-id <id>]
    (skeleton; does NOT execute pipeline)

  run_pipeline.sh --post-gate-only --run-dir <RUN_DIR> [--run-id <id>]
    Observer-only validation:
      - reads export_path from outputs/08.json (.data.export_path)
      - enforces T=L=E (T=total_articles, L=len(articles), E=pdf count under export_path)
      - verifies sha256sum -c checksums.sha256 in export_path
      - writes audit JSON to _audit/claude_code/reports/run_pipeline_{run_id}.json

Exit codes:
  0  success (post-gate-only)
  2  usage/pre-gate failure / skeleton not implemented path
  3  post-gate failure
USAGE
}

ISSUE=""
RUN_ID=""
POST_GATE_ONLY="0"
RUN_DIR=""

while [[ $# -gt 0 ]]; do
  case "$1" in
    --issue)
      ISSUE="${2:-}"; shift 2;;
    --run-id)
      RUN_ID="${2:-}"; shift 2;;
    --post-gate-only)
      POST_GATE_ONLY="1"; shift 1;;
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
  "ts_utc": "${ts_utc()}",
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

main() {
  preflight_repo || exit 2

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

  # Skeleton non-executing default path
  if [[ -z "${ISSUE}" ]]; then
    echo "Missing required --issue" >&2
    usage
    exit 2
  fi

  ensure_audit_dir
  echo "run-pipeline skeleton: contract committed, post-gate-only implemented."
  echo "NOT IMPLEMENTED: pipeline execution is intentionally disabled in this step."
  echo "Issue: ${ISSUE}"
  echo "Run-ID: ${RUN_ID:-<unset>}"
  exit 2
}

main "$@"
