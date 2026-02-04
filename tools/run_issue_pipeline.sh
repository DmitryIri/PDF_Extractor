#!/usr/bin/env bash
# ---------------------------------------------------------------------------
# tools/run_issue_pipeline.sh
#
# Universal entrypoint — runs the full 8-step PDF Extractor pipeline
# for any journal issue (Mg, Na, Mh, …).
#
# Usage:
#   tools/run_issue_pipeline.sh \
#     --journal-code  <Mg|Na|Mh|…> \
#     --issue-id      <mg_2025_12|…> \
#     --pdf-path      </srv/pdf-extractor/tmp/…pdf> \
#     [--run-id       <id>]           # default: manual_$(date -u +%Y%m%d_%H%M%S)
#
# On success : prints export_path and hints to articles/ / checksums.sha256.
# On failure : exits with the failing agent's exit code; prints the step
#              number and the path to the relevant log file.
# ---------------------------------------------------------------------------
set -euo pipefail

# ── Defaults (overridable via environment) ─────────────────────────────────
REPO="${REPO:-/opt/projects/pdf-extractor}"
PY="${PY:-/srv/pdf-extractor/venv/bin/python}"
RUNS_ROOT="${RUNS_ROOT:-/srv/pdf-extractor/runs}"

# ── Usage ──────────────────────────────────────────────────────────────────
usage() {
    cat >&2 <<'USAGE'
Usage: run_issue_pipeline.sh \
  --journal-code  <code>     (required)  e.g. Mg, Na, Mh
  --issue-id      <id>       (required)  e.g. mg_2025_12
  --pdf-path      <path>     (required)  e.g. /srv/pdf-extractor/tmp/Mg_2025-12.pdf
  --run-id        <id>       (optional)  default: manual_YYYYMMDD_HHMMSS (UTC)
USAGE
}

# ── Argument parsing ───────────────────────────────────────────────────────
JOURNAL_CODE=""
ISSUE_ID=""
PDF_PATH=""
RUN_ID=""

while [[ $# -gt 0 ]]; do
    case "$1" in
        --journal-code)  JOURNAL_CODE="$2"; shift 2 ;;
        --issue-id)      ISSUE_ID="$2";     shift 2 ;;
        --pdf-path)      PDF_PATH="$2";     shift 2 ;;
        --run-id)        RUN_ID="$2";       shift 2 ;;
        --help|-h)       usage; exit 0 ;;
        *)               echo "[ERROR] Unknown option: $1" >&2; usage; exit 1 ;;
    esac
done

# ── Validate required args ─────────────────────────────────────────────────
_missing=()
[[ -z "$JOURNAL_CODE" ]] && _missing+=(--journal-code)
[[ -z "$ISSUE_ID"     ]] && _missing+=(--issue-id)
[[ -z "$PDF_PATH"     ]] && _missing+=(--pdf-path)
if [[ ${#_missing[@]} -gt 0 ]]; then
    echo "[ERROR] Missing required flags: ${_missing[*]}" >&2
    usage
    exit 1
fi

# ── Default run_id ─────────────────────────────────────────────────────────
RUN_ID="${RUN_ID:-manual_$(date -u +%Y%m%d_%H%M%S)}"

# ── Precondition checks ────────────────────────────────────────────────────
# Run before any side effects (mkdir, file writes).  Each prints a clear
# error and exits immediately.
command -v jq    >/dev/null 2>&1 || { echo "[ERROR] jq not found. Install jq and retry." >&2; exit 1; }
[[ -x "$PY"    ]]               || { echo "[ERROR] Python not executable: $PY" >&2; exit 1; }
[[ -d "$REPO"  ]]               || { echo "[ERROR] REPO directory not found: $REPO" >&2; exit 1; }
[[ -r "$PDF_PATH" ]]            || { echo "[ERROR] PDF not readable: $PDF_PATH" >&2; exit 1; }

# ── Paths ──────────────────────────────────────────────────────────────────
RUN_DIR="${RUNS_ROOT}/${ISSUE_ID}_${RUN_ID}"

# ── Banner ─────────────────────────────────────────────────────────────────
echo "==================================================================="
echo "PDF Extractor — Full Pipeline"
echo "==================================================================="
echo "  Journal code : $JOURNAL_CODE"
echo "  Issue ID     : $ISSUE_ID"
echo "  PDF path     : $PDF_PATH"
echo "  Run ID       : $RUN_ID"
echo "  Run dir      : $RUN_DIR"
echo "==================================================================="
echo ""

# ── Prepare RUN_DIR ────────────────────────────────────────────────────────
mkdir -p "${RUN_DIR}"/{input,outputs,logs}

# ── Generate input.json ────────────────────────────────────────────────────
cat > "${RUN_DIR}/input/input.json" <<EOF
{
  "issue_id": "${ISSUE_ID}",
  "journal_code": "${JOURNAL_CODE}",
  "pdf_path": "${PDF_PATH}"
}
EOF

# ── run_step: execute one pipeline component ───────────────────────────────
# Args:  step_number  display_name  agent_script_path  input_file
# I/O:   output  → outputs/0N.json
#        stderr  → logs/0N.log
run_step() {
    local step="$1"
    local name="$2"
    local script="$3"
    local input="$4"
    local output="${RUN_DIR}/outputs/0${step}.json"
    local log="${RUN_DIR}/logs/0${step}.log"

    echo -n "[step ${step}/8] ${name} … "

    set +e
    PYTHONPATH="$REPO" "$PY" "$REPO/$script" < "$input" > "$output" 2> "$log"
    local rc=$?
    set -e

    if [[ $rc -ne 0 ]]; then
        echo "[FAILED] (exit ${rc})"
        echo "" >&2
        echo "[ERROR] ${name} failed (exit code ${rc})" >&2
        echo "[ERROR] Log:    ${log}" >&2
        echo "[ERROR] Output: ${output}" >&2
        exit $rc
    fi

    echo "[OK]"
}

# ── Execute 8-step pipeline ────────────────────────────────────────────────
run_step 1 "InputValidator"     "agents/input_validator/validator.py"     "${RUN_DIR}/input/input.json"
run_step 2 "PDFInspector"       "agents/pdf_inspector/inspector.py"       "${RUN_DIR}/outputs/01.json"
run_step 3 "MetadataExtractor"  "agents/metadata_extractor/extractor.py"  "${RUN_DIR}/outputs/02.json"
run_step 4 "BoundaryDetector"   "agents/boundary_detector/detector.py"    "${RUN_DIR}/outputs/03.json"
run_step 5 "Splitter"           "agents/splitter/splitter.py"             "${RUN_DIR}/outputs/04.json"

# ── Merge: inject splitter output_dir into BoundaryDetector envelope ──────
# MetadataVerifier needs both the boundary data AND the path to the split
# PDFs.  Convention: splitter_output_dir is added as .data.splitter_output_dir
echo -n "[merge ] BoundaryDetector + splitter output_dir → 05_merged … "
SPLITTER_OUTPUT_DIR=$(jq -r '.data.output_dir' "${RUN_DIR}/outputs/05.json")
jq --arg dir "$SPLITTER_OUTPUT_DIR" '.data.splitter_output_dir = $dir' \
    "${RUN_DIR}/outputs/04.json" \
    > "${RUN_DIR}/outputs/05_merged.json"
echo "[OK]"

run_step 6 "MetadataVerifier"   "agents/metadata_verifier/verifier.py"    "${RUN_DIR}/outputs/05_merged.json"
run_step 7 "OutputBuilder"      "agents/output_builder/builder.py"        "${RUN_DIR}/outputs/06.json"
run_step 8 "OutputValidator"    "agents/output_validator/validator.py"    "${RUN_DIR}/outputs/07.json"

# ── Success summary ────────────────────────────────────────────────────────
EXPORT_PATH=$(jq -r '.data.export_path // .export_path // empty' "${RUN_DIR}/outputs/07.json")

echo ""
echo "==================================================================="
echo "[OK] Full pipeline completed"
echo "==================================================================="
echo "  Journal code : $JOURNAL_CODE"
echo "  Issue ID     : $ISSUE_ID"
echo "  Run dir      : $RUN_DIR"
echo "  Export path  : $EXPORT_PATH"
echo ""
echo "  Articles     : ${EXPORT_PATH}/articles/"
echo "  Checksums    : ${EXPORT_PATH}/checksums.sha256"
echo "==================================================================="
