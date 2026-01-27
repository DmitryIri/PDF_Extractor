#!/bin/bash
#
# Integration tests for OutputValidator v1.0.0
#
# Tests validation against real export structures (or mocked ones).
# Exit code 0 = all tests pass, 1 = any test fails

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
VALIDATOR="$PROJECT_ROOT/agents/output_validator/validator.py"

# Use project venv if available, otherwise system python3
if [ -f "$PROJECT_ROOT/.venv/bin/python" ]; then
    PYTHON="$PROJECT_ROOT/.venv/bin/python"
else
    PYTHON="python3"
fi

# Temp directory for test artifacts
TEST_DIR=$(mktemp -d)
trap "rm -rf $TEST_DIR" EXIT

echo "========================================="
echo "OutputValidator Integration Tests"
echo "========================================="
echo "Test directory: $TEST_DIR"
echo

# Helper: Create minimal export structure
create_test_export() {
    local export_path="$1"
    local num_articles="$2"

    mkdir -p "$export_path/articles"
    mkdir -p "$export_path/manifest"

    # Create dummy PDF files with valid surname format
    local surnames=("Ivanov" "Petrov" "Sidorov" "Kuznetsov" "Smirnov" "Popov")
    for i in $(seq 1 $num_articles); do
        local idx=$(printf "%03d" $i)
        local next_idx=$(printf "%03d" $((i + 2)))
        local surname_idx=$(( (i - 1) % ${#surnames[@]} ))
        local surname="${surnames[$surname_idx]}"
        echo "dummy pdf content $i" > "$export_path/articles/Mg_2025-12_${idx}-${next_idx}_${surname}.pdf"
    done

    # Create checksums.sha256
    (cd "$export_path/articles" && sha256sum *.pdf) > "$export_path/checksums.sha256"

    # Create README.md
    echo "# Test Export" > "$export_path/README.md"
}

# Helper: Create input JSON for validator
create_validator_input() {
    local export_path="$1"
    local num_articles="$2"

    # Build articles array using jq
    local surnames=("Ivanov" "Petrov" "Sidorov" "Kuznetsov" "Smirnov" "Popov")
    local articles_json="[]"
    for i in $(seq 1 $num_articles); do
        local idx=$(printf "%03d" $i)
        local next_idx=$(printf "%03d" $((i + 2)))
        local surname_idx=$(( (i - 1) % ${#surnames[@]} ))
        local surname="${surnames[$surname_idx]}"
        local filename="Mg_2025-12_${idx}-${next_idx}_${surname}.pdf"
        local checksum=$(grep "$filename" "$export_path/checksums.sha256" | awk '{print $1}')

        articles_json=$(echo "$articles_json" | jq \
            --arg fn "$filename" \
            --arg mk "research" \
            --argjson sp "$i" \
            --argjson ep "$((i + 2))" \
            --arg cs "$checksum" \
            '. += [{"filename": $fn, "material_kind": $mk, "start_page": $sp, "end_page": $ep, "sha256_checksum": $cs}]')
    done

    # Create full input using jq
    jq -n \
        --arg issue_id "mg_2025_12" \
        --arg export_path "$export_path" \
        --argjson total "$num_articles" \
        --argjson articles "$articles_json" \
        '{
            status: "success",
            component: "OutputBuilder",
            version: "1.0.0",
            data: {
                issue_id: $issue_id,
                export_path: $export_path,
                total_articles: $total,
                articles: $articles
            }
        }'
}

# Test counter
TESTS_RUN=0
TESTS_PASSED=0
TESTS_FAILED=0

# Helper: Run test
run_test() {
    local test_name="$1"
    local expected_exit="$2"
    local input_json="$3"

    TESTS_RUN=$((TESTS_RUN + 1))
    echo -n "Test $TESTS_RUN: $test_name ... "

    set +e
    output=$(echo "$input_json" | $PYTHON "$VALIDATOR" 2>&1)
    actual_exit=$?
    set -e

    if [ $actual_exit -eq $expected_exit ]; then
        echo "✅ PASS"
        TESTS_PASSED=$((TESTS_PASSED + 1))
    else
        echo "❌ FAIL"
        echo "  Expected exit code: $expected_exit"
        echo "  Actual exit code: $actual_exit"
        echo "  Output:"
        echo "$output" | sed 's/^/    /'
        TESTS_FAILED=$((TESTS_FAILED + 1))
    fi
}

#
# Test 1: Valid export (T=L=E satisfied)
#
echo "[Test 1] Valid export with T=L=E satisfied"
export1="$TEST_DIR/export1"
create_test_export "$export1" 3
input1=$(create_validator_input "$export1" 3)
run_test "Valid export" 0 "$input1"
echo

#
# Test 2: T=L=E violation (total_articles mismatch)
#
echo "[Test 2] T=L=E violation (T ≠ L)"
export2="$TEST_DIR/export2"
create_test_export "$export2" 3
# Manually craft input with wrong total_articles
input2=$(cat <<EOF
{
  "issue_id": "mg_2025_12",
  "export_path": "$export2",
  "total_articles": 5,
  "articles": [
    {"filename":"Mg_2025-12_001-003_Test1.pdf","material_kind":"research","sha256_checksum":"abc123"},
    {"filename":"Mg_2025-12_002-004_Test2.pdf","material_kind":"research","sha256_checksum":"def456"},
    {"filename":"Mg_2025-12_003-005_Test3.pdf","material_kind":"research","sha256_checksum":"ghi789"}
  ]
}
EOF
)
run_test "T=L=E violation (T≠L)" 30 "$input2"
echo

#
# Test 3: Missing PDF file (T=L but L≠E)
#
echo "[Test 3] Missing PDF file (L ≠ E)"
export3="$TEST_DIR/export3"
create_test_export "$export3" 3
# Delete one PDF to cause L≠E (use the second file, whatever it's named)
rm "$export3/articles/Mg_2025-12_002-004_Petrov.pdf"
input3=$(create_validator_input "$export3" 3)
run_test "Missing PDF file (L≠E)" 30 "$input3"
echo

#
# Test 4: Invalid filename format (research pattern violation)
#
echo "[Test 4] Invalid filename format"
export4="$TEST_DIR/export4"
mkdir -p "$export4/articles" "$export4/manifest"
echo "dummy" > "$export4/articles/INVALID_FILENAME.pdf"
sha256sum "$export4/articles/INVALID_FILENAME.pdf" > "$export4/checksums.sha256"
echo "# Test" > "$export4/README.md"

input4=$(cat <<EOF
{
  "issue_id": "mg_2025_12",
  "export_path": "$export4",
  "total_articles": 1,
  "articles": [
    {"filename":"INVALID_FILENAME.pdf","material_kind":"research","sha256_checksum":"abc123"}
  ]
}
EOF
)
run_test "Invalid filename format" 30 "$input4"
echo

#
# Test 5: Checksum mismatch (corrupt PDF)
#
echo "[Test 5] Checksum mismatch"
export5="$TEST_DIR/export5"
create_test_export "$export5" 1
# Corrupt the PDF after checksums were computed
echo "CORRUPTED" >> "$export5/articles/Mg_2025-12_001-003_Test1.pdf"
input5=$(create_validator_input "$export5" 1)
run_test "Checksum mismatch" 30 "$input5"
echo

#
# Test 6: Missing export structure (no checksums.sha256)
#
echo "[Test 6] Missing export structure component"
export6="$TEST_DIR/export6"
mkdir -p "$export6/articles" "$export6/manifest"
echo "dummy" > "$export6/articles/Mg_2025-12_001-003_Test1.pdf"
echo "# Test" > "$export6/README.md"
# Missing: checksums.sha256

input6=$(cat <<EOF
{
  "issue_id": "mg_2025_12",
  "export_path": "$export6",
  "total_articles": 1,
  "articles": [
    {"filename":"Mg_2025-12_001-003_Test1.pdf","material_kind":"research","sha256_checksum":"abc123"}
  ]
}
EOF
)
run_test "Missing checksums.sha256" 30 "$input6"
echo

#
# Test 7: Service material filename (Contents)
#
echo "[Test 7] Service material filename (Contents)"
export7="$TEST_DIR/export7"
mkdir -p "$export7/articles" "$export7/manifest"
echo "contents pdf" > "$export7/articles/Mg_2025-12_001-004_Contents.pdf"
(cd "$export7/articles" && sha256sum *.pdf) > "$export7/checksums.sha256"
echo "# Test" > "$export7/README.md"

checksum7=$(grep "Contents" "$export7/checksums.sha256" | awk '{print $1}')
input7=$(cat <<EOF
{
  "issue_id": "mg_2025_12",
  "export_path": "$export7",
  "total_articles": 1,
  "articles": [
    {"filename":"Mg_2025-12_001-004_Contents.pdf","material_kind":"contents","sha256_checksum":"$checksum7"}
  ]
}
EOF
)
run_test "Service material (Contents)" 0 "$input7"
echo

#
# Test 8: Empty stdin
#
echo "[Test 8] Empty stdin"
run_test "Empty stdin" 10 ""
echo

#
# Summary
#
echo "========================================="
echo "Test Summary"
echo "========================================="
echo "Tests run:    $TESTS_RUN"
echo "Tests passed: $TESTS_PASSED"
echo "Tests failed: $TESTS_FAILED"
echo

if [ $TESTS_FAILED -eq 0 ]; then
    echo "✅ ALL TESTS PASSED"
    exit 0
else
    echo "❌ SOME TESTS FAILED"
    exit 1
fi
