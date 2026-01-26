#!/bin/bash
# PDF Extractor — Golden Test for Material Classification
# Verifies exact filename match against reference canonical manifest
#
# Test Steps:
# 1. Load reference manifest (ground truth)
# 2. Run pipeline components to generate filenames for Mg_2025-12
# 3. Compare generated filenames EXACTLY to canonical set
# 4. Assert specific key files exist with correct material_kind
# 5. Print surname source + evidence for research examples
#
# Exit Codes:
# 0 = All tests passed (exact match achieved)
# 1 = Test failed (mismatch or error)

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
REFERENCE_MANIFEST="$PROJECT_ROOT/docs/state/reference_inputs_manifest_mg_2025_12_v_1_0.json"
GOLDEN_ANCHORS="$PROJECT_ROOT/golden_tests/mg_2025_12_anchors.json"

echo "========================================="
echo "Material Classification Golden Test"
echo "========================================="
echo

# Step 1: Validate reference manifest exists
echo "[1/5] Validating reference manifest..."
if [[ ! -f "$REFERENCE_MANIFEST" ]]; then
    echo "ERROR: Reference manifest not found: $REFERENCE_MANIFEST"
    exit 1
fi

TOTAL_REFERENCE=$(jq '.meta.total_files' "$REFERENCE_MANIFEST")
echo "✓ Reference manifest loaded: $TOTAL_REFERENCE articles"
echo

# Step 2: Extract canonical filename set from reference manifest
echo "[2/5] Extracting canonical filename set..."
CANONICAL_FILENAMES=$(jq -r '.articles[].filename' "$REFERENCE_MANIFEST" | sort)
CANONICAL_COUNT=$(echo "$CANONICAL_FILENAMES" | wc -l)
echo "✓ Canonical filenames: $CANONICAL_COUNT"
echo

# Step 3: Run MetadataExtractor → BoundaryDetector to generate filenames
echo "[3/5] Running pipeline to generate filenames..."

# Check if source PDF exists (if not, we'll use golden anchors directly)
SOURCE_PDF_CANDIDATES=(
    "$PROJECT_ROOT/_audit/reference_inputs/mg_2025_12_source/Mg_2025-12.pdf"
    "/srv/pdf-extractor/test_data/Mg_2025-12.pdf"
)

SOURCE_PDF=""
for candidate in "${SOURCE_PDF_CANDIDATES[@]}"; do
    if [[ -f "$candidate" ]]; then
        SOURCE_PDF="$candidate"
        break
    fi
done

if [[ -z "$SOURCE_PDF" ]]; then
    echo "⚠ Source PDF not found, using golden anchors directly"

    # Use pre-existing golden anchors
    if [[ ! -f "$GOLDEN_ANCHORS" ]]; then
        echo "ERROR: Golden anchors not found: $GOLDEN_ANCHORS"
        exit 1
    fi

    ANCHORS_JSON=$(cat "$GOLDEN_ANCHORS")
else
    echo "✓ Source PDF found: $SOURCE_PDF"

    # Run MetadataExtractor
    EXTRACTOR_INPUT=$(jq -n --arg pdf "$SOURCE_PDF" '{issue_id: "mg_2025_12", pdf: {path: $pdf}}')
    EXTRACTOR_OUTPUT=$(echo "$EXTRACTOR_INPUT" | python3 "$PROJECT_ROOT/agents/metadata_extractor/extractor.py")

    # Check for errors
    EXTRACTOR_STATUS=$(echo "$EXTRACTOR_OUTPUT" | jq -r '.status')
    if [[ "$EXTRACTOR_STATUS" != "success" ]]; then
        echo "ERROR: MetadataExtractor failed"
        echo "$EXTRACTOR_OUTPUT" | jq
        exit 1
    fi

    ANCHORS_JSON="$EXTRACTOR_OUTPUT"
fi

echo "✓ Anchors loaded"

# Run BoundaryDetector
DETECTOR_OUTPUT=$(echo "$ANCHORS_JSON" | python3 "$PROJECT_ROOT/agents/boundary_detector/detector.py")

DETECTOR_STATUS=$(echo "$DETECTOR_OUTPUT" | jq -r '.status')
if [[ "$DETECTOR_STATUS" != "success" ]]; then
    echo "ERROR: BoundaryDetector failed"
    echo "$DETECTOR_OUTPUT" | jq
    exit 1
fi

echo "✓ BoundaryDetector completed"

# Extract boundary_ranges with material_kind
BOUNDARY_RANGES=$(echo "$DETECTOR_OUTPUT" | jq '.data.boundary_ranges')
DETECTED_COUNT=$(echo "$BOUNDARY_RANGES" | jq 'length')

echo "✓ Articles detected: $DETECTED_COUNT"

# Build VerifiedArticleManifest input for MetadataVerifier (simulated)
# Note: In real pipeline, this would come from Splitter → MetadataVerifier
# For filename generation, we only need boundary_ranges + anchors

VERIFIER_INPUT=$(jq -n \
    --arg issue_id "mg_2025_12" \
    --arg issue_prefix "Mg_2025-12" \
    --argjson boundary_ranges "$BOUNDARY_RANGES" \
    --argjson anchors "$(echo "$ANCHORS_JSON" | jq '.data.anchors')" \
    '{
        issue_id: $issue_id,
        issue_prefix: $issue_prefix,
        boundary_ranges: $boundary_ranges,
        anchors: $anchors
    }')

# For filename generation without actual splitter files, we'll compute expected filenames directly
# This mimics MetadataVerifier logic

GENERATED_FILENAMES=$(echo "$VERIFIER_INPUT" | python3 -c "
import json
import sys

data = json.load(sys.stdin)
issue_prefix = data['issue_prefix']
boundary_ranges = data['boundary_ranges']
anchors = data['anchors']

# Import transliteration from verifier
sys.path.insert(0, '$PROJECT_ROOT/agents/metadata_verifier')
from verifier import _extract_surname_for_research, _sanitize_surname

filenames = []

for br in boundary_ranges:
    article_id = br['id']
    from_page = br['from']
    to_page = br['to']
    material_kind = br['material_kind']

    from_p = str(from_page).zfill(3)
    to_p = str(to_page).zfill(3)

    if material_kind == 'research':
        try:
            surname_data = _extract_surname_for_research(from_page, anchors)
            surname = surname_data['first_author_surname']
            sanitized = _sanitize_surname(surname)
            filename = f'{issue_prefix}_{from_p}-{to_p}_{sanitized}.pdf'
        except SystemExit:
            # Fallback if no authors found
            filename = f'{issue_prefix}_{from_p}-{to_p}_UNKNOWN.pdf'
    elif material_kind == 'contents':
        filename = f'{issue_prefix}_{from_p}-{to_p}_Contents.pdf'
    elif material_kind == 'editorial':
        filename = f'{issue_prefix}_{from_p}-{to_p}_Editorial.pdf'
    elif material_kind == 'digest':
        filename = f'{issue_prefix}_{from_p}-{to_p}_Digest.pdf'
    else:
        filename = f'{issue_prefix}_{from_p}-{to_p}_INVALID.pdf'

    filenames.append(filename)

for fn in sorted(filenames):
    print(fn)
")

GENERATED_COUNT=$(echo "$GENERATED_FILENAMES" | wc -l)

echo "✓ Filenames generated: $GENERATED_COUNT"
echo

# Step 4: Compare generated vs canonical filenames
echo "[4/5] Comparing filename sets..."

# Exact set comparison
CANONICAL_SORTED=$(echo "$CANONICAL_FILENAMES" | sort)
GENERATED_SORTED=$(echo "$GENERATED_FILENAMES" | sort)

if [[ "$CANONICAL_SORTED" == "$GENERATED_SORTED" ]]; then
    echo "✅ EXACT MATCH: Generated filenames match canonical set perfectly!"
    echo
else
    echo "❌ MISMATCH: Generated filenames do not match canonical set"
    echo
    echo "Expected (canonical):"
    echo "$CANONICAL_SORTED"
    echo
    echo "Got (generated):"
    echo "$GENERATED_SORTED"
    echo

    echo "Diff:"
    diff <(echo "$CANONICAL_SORTED") <(echo "$GENERATED_SORTED") || true
    exit 1
fi

# Step 5: Assert specific key files
echo "[5/5] Asserting specific key files..."

# Helper function to check filename in set
check_filename() {
    local filename="$1"
    local expected_material="$2"

    if echo "$GENERATED_FILENAMES" | grep -q "^$filename$"; then
        # Verify material_kind from boundary_ranges
        local actual_material=$(echo "$BOUNDARY_RANGES" | jq -r --arg fn "$filename" --arg prefix "Mg_2025-12" '
            .[] | select(
                ($prefix + "_" + (.from | tostring | (if (. | tostring | length) == 1 then "00" + (. | tostring) elif (. | tostring | length) == 2 then "0" + (. | tostring) else (. | tostring) end)) + "-" + (.to | tostring | (if (. | tostring | length) == 1 then "00" + (. | tostring) elif (. | tostring | length) == 2 then "0" + (. | tostring) else (. | tostring) end))) | test("^" + $fn[0:18])
            ) | .material_kind
        ' | head -1)

        if [[ "$actual_material" == "$expected_material" ]]; then
            echo "  ✓ $filename (material_kind=$expected_material)"
        else
            echo "  ❌ $filename exists but material_kind=$actual_material (expected $expected_material)"
            exit 1
        fi
    else
        echo "  ❌ $filename NOT FOUND"
        exit 1
    fi
}

check_filename "Mg_2025-12_001-004_Contents.pdf" "contents"
check_filename "Mg_2025-12_005-005_Editorial.pdf" "editorial"
check_filename "Mg_2025-12_016-027_Burykina.pdf" "research"
check_filename "Mg_2025-12_067-073_Zaklyazminskaya.pdf" "research"

echo

# Print surname source + evidence for research examples
echo "Research Article Surname Sources:"
echo "---------------------------------"

for article_page in 16 67; do
    article_info=$(echo "$BOUNDARY_RANGES" | jq --arg page "$article_page" '
        .[] | select(.from == ($page | tonumber))
    ')

    if [[ -n "$article_info" ]]; then
        article_id=$(echo "$article_info" | jq -r '.id')
        from_page=$(echo "$article_info" | jq -r '.from')
        to_page=$(echo "$article_info" | jq -r '.to')

        # Extract surname data
        surname_data=$(echo "$VERIFIER_INPUT" | python3 -c "
import json
import sys

data = json.load(sys.stdin)
anchors = data['anchors']
from_page = $from_page

sys.path.insert(0, '$PROJECT_ROOT/agents/metadata_verifier')
from verifier import _extract_surname_for_research

try:
    surname_data = _extract_surname_for_research(from_page, anchors)
    print(json.dumps(surname_data, ensure_ascii=False))
except SystemExit:
    print(json.dumps({'error': 'no_authors_found'}, ensure_ascii=False))
")

        surname=$(echo "$surname_data" | jq -r '.first_author_surname // "N/A"')
        source=$(echo "$surname_data" | jq -r '.first_author_surname_source // "N/A"')
        anchor_type=$(echo "$surname_data" | jq -r '.evidence.anchor_type // "N/A"')
        anchor_page=$(echo "$surname_data" | jq -r '.evidence.anchor_page // "N/A"')

        echo "  Article ${article_id} (pages ${from_page}-${to_page}):"
        echo "    Surname: $surname"
        echo "    Source: $source"
        echo "    Evidence: anchor_type=$anchor_type, anchor_page=$anchor_page"
        echo
    fi
done

echo "========================================="
echo "✅ ALL TESTS PASSED"
echo "========================================="
echo
echo "Summary:"
echo "  Reference articles: $CANONICAL_COUNT"
echo "  Generated articles: $GENERATED_COUNT"
echo "  Match: EXACT"
echo

exit 0
