#!/usr/bin/env bash
# Test OutputBuilder component
#
# Usage: ./tests/test_output_builder.sh
#
# Tests:
# 1. Happy path: valid input with 2 articles
# 2. Negative: missing required field
# 3. Negative: non-existent source PDF

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
BUILDER="$PROJECT_ROOT/agents/output_builder/builder.py"

# Colors for output
GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Test counters
TESTS_PASSED=0
TESTS_FAILED=0

echo "=== OutputBuilder Tests ==="
echo

# Helper: run test
run_test() {
    local test_name="$1"
    local expected_exit_code="$2"
    local input_json="$3"

    echo -n "Test: $test_name ... "

    # Run builder
    set +e
    output=$(echo "$input_json" | python3 "$BUILDER" 2>&1)
    exit_code=$?
    set -e

    if [ "$exit_code" -eq "$expected_exit_code" ]; then
        echo -e "${GREEN}PASS${NC} (exit code: $exit_code)"
        TESTS_PASSED=$((TESTS_PASSED + 1))
        return 0
    else
        echo -e "${RED}FAIL${NC} (expected exit code $expected_exit_code, got $exit_code)"
        echo "Output: $output"
        TESTS_FAILED=$((TESTS_FAILED + 1))
        return 1
    fi
}

# Test 1: Happy path (with real PDF files)
echo "--- Test 1: Happy path (requires real PDF files) ---"

# Check if test PDFs exist
TEST_ARTICLES_DIR="/srv/pdf-extractor/tmp/articles"
TEST_PDF_A01="$TEST_ARTICLES_DIR/mg_2025_12_a01.pdf"
TEST_PDF_A02="$TEST_ARTICLES_DIR/mg_2025_12_a02.pdf"

if [ -f "$TEST_PDF_A01" ] && [ -f "$TEST_PDF_A02" ]; then
    # Compute actual SHA256 for test files
    SHA256_A01=$(sha256sum "$TEST_PDF_A01" | awk '{print $1}')
    SHA256_A02=$(sha256sum "$TEST_PDF_A02" | awk '{print $1}')
    SIZE_A01=$(stat -f%z "$TEST_PDF_A01" 2>/dev/null || stat -c%s "$TEST_PDF_A01")
    SIZE_A02=$(stat -f%z "$TEST_PDF_A02" 2>/dev/null || stat -c%s "$TEST_PDF_A02")

    # Build input JSON with actual checksums
    INPUT_JSON=$(cat <<EOF
{
  "journal_code": "Mg",
  "issue_prefix": "Mg_2025-12",
  "total_articles": 2,
  "articles": [
    {
      "article_id": "a01",
      "from_page": 5,
      "to_page": 5,
      "material_kind": "research",
      "first_author_surname": "Barysheva",
      "expected_filename": "Mg_2025-12_005-005_Barysheva.pdf",
      "splitter_output": {
        "path": "$TEST_PDF_A01",
        "bytes": $SIZE_A01,
        "sha256": "$SHA256_A01"
      }
    },
    {
      "article_id": "a02",
      "from_page": 6,
      "to_page": 15,
      "material_kind": "research",
      "first_author_surname": "Andreeva",
      "expected_filename": "Mg_2025-12_006-015_Andreeva.pdf",
      "splitter_output": {
        "path": "$TEST_PDF_A02",
        "bytes": $SIZE_A02,
        "sha256": "$SHA256_A02"
      }
    }
  ]
}
EOF
)

    run_test "Happy path with real PDFs" 0 "$INPUT_JSON"

    # If test passed, show export path
    if [ $? -eq 0 ]; then
        # Extract export_path from output
        EXPORT_PATH=$(echo "$output" | python3 -c "import sys, json; data = json.load(sys.stdin); print(data.get('data', {}).get('export_path', 'N/A'))" 2>/dev/null || echo "N/A")
        echo -e "${YELLOW}  Export path: $EXPORT_PATH${NC}"

        # Verify export structure
        if [ -d "$EXPORT_PATH" ]; then
            echo -e "${YELLOW}  Export structure:${NC}"
            ls -lah "$EXPORT_PATH" 2>/dev/null || true
            ls -lah "$EXPORT_PATH/articles/" 2>/dev/null || true
            ls -lah "$EXPORT_PATH/manifest/" 2>/dev/null || true
        fi
    fi
else
    echo -e "${YELLOW}SKIP${NC} (test PDFs not found: $TEST_PDF_A01, $TEST_PDF_A02)"
    echo "  Run Splitter first to generate test artifacts"
fi

echo

# Test 2: Negative - missing required field
echo "--- Test 2: Negative - missing journal_code ---"

INPUT_JSON_MISSING_FIELD=$(cat <<'EOF'
{
  "issue_prefix": "Mg_2025-12",
  "articles": []
}
EOF
)

run_test "Missing journal_code" 10 "$INPUT_JSON_MISSING_FIELD"
echo

# Test 3: Negative - invalid journal_code format
echo "--- Test 3: Negative - invalid journal_code (not 2 letters) ---"

INPUT_JSON_INVALID_CODE=$(cat <<'EOF'
{
  "journal_code": "ABC",
  "issue_prefix": "Mg_2025-12",
  "articles": []
}
EOF
)

run_test "Invalid journal_code format" 10 "$INPUT_JSON_INVALID_CODE"
echo

# Test 4: Negative - invalid issue_prefix format
echo "--- Test 4: Negative - invalid issue_prefix format ---"

INPUT_JSON_INVALID_PREFIX=$(cat <<'EOF'
{
  "journal_code": "Mg",
  "issue_prefix": "Invalid_Format",
  "articles": []
}
EOF
)

run_test "Invalid issue_prefix format" 10 "$INPUT_JSON_INVALID_PREFIX"
echo

# Test 5: Negative - non-existent source PDF
echo "--- Test 5: Negative - non-existent source PDF ---"

INPUT_JSON_MISSING_PDF=$(cat <<'EOF'
{
  "journal_code": "Mg",
  "issue_prefix": "Mg_2025-12",
  "articles": [
    {
      "article_id": "a99",
      "from_page": 1,
      "to_page": 1,
      "material_kind": "research",
      "first_author_surname": "NonExistent",
      "expected_filename": "Mg_2025-12_001-001_NonExistent.pdf",
      "splitter_output": {
        "path": "/tmp/nonexistent_file_12345.pdf",
        "bytes": 1000,
        "sha256": "dummy_sha"
      }
    }
  ]
}
EOF
)

run_test "Non-existent source PDF" 40 "$INPUT_JSON_MISSING_PDF"
echo

# Summary
echo "=== Test Summary ==="
echo -e "Passed: ${GREEN}$TESTS_PASSED${NC}"
echo -e "Failed: ${RED}$TESTS_FAILED${NC}"
echo

if [ "$TESTS_FAILED" -eq 0 ]; then
    echo -e "${GREEN}All tests passed!${NC}"
    exit 0
else
    echo -e "${RED}Some tests failed!${NC}"
    exit 1
fi
