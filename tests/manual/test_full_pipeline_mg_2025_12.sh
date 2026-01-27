#!/usr/bin/env bash
set -euo pipefail

# Configuration
export PY="${PY:-/srv/pdf-extractor/venv/bin/python}"
export REPO="${REPO:-/opt/projects/pdf-extractor}"
export RUN_DIR="${RUN_DIR:-/srv/pdf-extractor/runs/mg_2025_12_full_pipeline_manual}"
export PDF_PATH="${PDF_PATH:-/srv/pdf-extractor/tmp/Mg_2025-12.pdf}"
export ISSUE_ID="${ISSUE_ID:-mg_2025_12}"
export ISSUE_PREFIX="${ISSUE_PREFIX:-Mg_2025-12}"

echo "==================================================================="
echo "Full Pipeline Sanity Run — mg_2025_12"
echo "==================================================================="
echo "RUN_DIR: $RUN_DIR"
echo "PDF_PATH: $PDF_PATH"
echo "ISSUE_ID: $ISSUE_ID"
echo "ISSUE_PREFIX: $ISSUE_PREFIX"
echo ""

# Create run directories
mkdir -p "$RUN_DIR"/{input,logs,outputs}

# Prepare input JSON
INPUT_JSON="$RUN_DIR/input/input_mg_2025_12.json"
cat > "$INPUT_JSON" << EOF
{
  "issue_id": "$ISSUE_ID",
  "journal_code": "Mg",
  "pdf_path": "$PDF_PATH"
}
EOF

echo "Input JSON created: $INPUT_JSON"
echo ""

# Function to run a component and check exit code
run_component() {
    local component_name="$1"
    local component_script="$2"
    local input_file="$3"
    local output_file="$4"
    local log_file="$5"

    echo "-------------------------------------------------------------------"
    echo "Running: $component_name"
    echo "-------------------------------------------------------------------"

    set +e
    "$PY" "$REPO/$component_script" < "$input_file" > "$output_file" 2> "$log_file"
    local rc=$?
    set -e

    if [ $rc -ne 0 ]; then
        echo "❌ FAILED: $component_name (exit_code=$rc)"
        echo "   Log: $log_file"
        echo "   Output: $output_file"
        exit $rc
    fi

    echo "✅ SUCCESS: $component_name (exit_code=0)"
    echo "   Output: $output_file"
    echo "   Log: $log_file"
    echo ""
}

# Execute pipeline components sequentially
run_component "InputValidator" \
    "agents/input_validator/validator.py" \
    "$INPUT_JSON" \
    "$RUN_DIR/outputs/01_input_validator.json" \
    "$RUN_DIR/logs/01_input_validator_stderr.log"

run_component "PDFInspector" \
    "agents/pdf_inspector/inspector.py" \
    "$RUN_DIR/outputs/01_input_validator.json" \
    "$RUN_DIR/outputs/02_pdf_inspector.json" \
    "$RUN_DIR/logs/02_pdf_inspector_stderr.log"

run_component "MetadataExtractor" \
    "agents/metadata_extractor/extractor.py" \
    "$RUN_DIR/outputs/02_pdf_inspector.json" \
    "$RUN_DIR/outputs/03_metadata_extractor.json" \
    "$RUN_DIR/logs/03_metadata_extractor_stderr.log"

run_component "BoundaryDetector" \
    "agents/boundary_detector/detector.py" \
    "$RUN_DIR/outputs/03_metadata_extractor.json" \
    "$RUN_DIR/outputs/04_boundary_detector.json" \
    "$RUN_DIR/logs/04_boundary_detector_stderr.log"

run_component "Splitter" \
    "agents/splitter/splitter.py" \
    "$RUN_DIR/outputs/04_boundary_detector.json" \
    "$RUN_DIR/outputs/05_splitter.json" \
    "$RUN_DIR/logs/05_splitter_stderr.log"

run_component "MetadataVerifier" \
    "agents/metadata_verifier/verifier.py" \
    "$RUN_DIR/outputs/05_splitter.json" \
    "$RUN_DIR/outputs/06_metadata_verifier.json" \
    "$RUN_DIR/logs/06_metadata_verifier_stderr.log"

run_component "OutputBuilder" \
    "agents/output_builder/builder.py" \
    "$RUN_DIR/outputs/06_metadata_verifier.json" \
    "$RUN_DIR/outputs/07_output_builder.json" \
    "$RUN_DIR/logs/07_output_builder_stderr.log"

run_component "OutputValidator" \
    "agents/output_validator/validator.py" \
    "$RUN_DIR/outputs/07_output_builder.json" \
    "$RUN_DIR/outputs/08_output_validator.json" \
    "$RUN_DIR/logs/08_output_validator_stderr.log"

echo "==================================================================="
echo "✅ FULL PIPELINE COMPLETED SUCCESSFULLY"
echo "==================================================================="
echo ""
echo "Results:"
echo "  - Outputs: $RUN_DIR/outputs/"
echo "  - Logs: $RUN_DIR/logs/"
echo ""

# Extract export path from OutputBuilder output
EXPORT_PATH=$(jq -r '.data.export_path // .export_path // empty' "$RUN_DIR/outputs/07_output_builder.json")
if [ -n "$EXPORT_PATH" ]; then
    echo "Export created at: $EXPORT_PATH"
    echo ""
    echo "Export structure:"
    tree -L 2 "$EXPORT_PATH" || ls -lR "$EXPORT_PATH"
fi
