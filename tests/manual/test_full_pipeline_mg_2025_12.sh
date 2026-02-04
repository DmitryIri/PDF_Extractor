#!/usr/bin/env bash
# ---------------------------------------------------------------------------
# tests/manual/test_full_pipeline_mg_2025_12.sh
#
# Golden-test wrapper for Mg_2025-12.
# Pipeline logic lives in tools/run_issue_pipeline.sh — this script only:
#   1. Sets the Mg_2025-12 parameters.
#   2. Invokes the universal pipeline runner.
#   3. Runs post-run verification against the known-good golden export.
# ---------------------------------------------------------------------------
set -euo pipefail

REPO="${REPO:-/opt/projects/pdf-extractor}"

# ── Golden-test parameters (do not change) ────────────────────────────────
JOURNAL_CODE="Mg"
ISSUE_ID="mg_2025_12"
PDF_PATH="/srv/pdf-extractor/tmp/Mg_2025-12.pdf"
RUN_ID="golden_mg_2025_12"

# Known-good export used as the comparison baseline.
GOLDEN_EXPORT="/srv/pdf-extractor/exports/Mg/2025/Mg_2025-12/exports/2026_01_27__21_53_35"

# ── Run pipeline ───────────────────────────────────────────────────────────
"${REPO}/tools/run_issue_pipeline.sh" \
    --journal-code  "$JOURNAL_CODE" \
    --issue-id      "$ISSUE_ID"      \
    --pdf-path      "$PDF_PATH"      \
    --run-id        "$RUN_ID"

# ── Derive paths from run output ───────────────────────────────────────────
RUN_DIR="/srv/pdf-extractor/runs/${ISSUE_ID}_${RUN_ID}"
EXPORT_PATH=$(jq -r '.data.export_path // .export_path // empty' "${RUN_DIR}/outputs/07.json")

if [[ -z "$EXPORT_PATH" || ! -d "$EXPORT_PATH" ]]; then
    echo "[ERROR] export_path missing or not a directory: ${EXPORT_PATH}" >&2
    exit 1
fi

# ── resolve_manifest: locate export_manifest.json ──────────────────────────
# Checks manifest/ subdir first, then export root; fails clearly if absent.
resolve_manifest() {
    if   [[ -f "$1/manifest/export_manifest.json" ]]; then echo "$1/manifest/export_manifest.json"
    elif [[ -f "$1/export_manifest.json"          ]]; then echo "$1/export_manifest.json"
    else  echo "[ERROR] No export_manifest.json found under $1" >&2; exit 1
    fi
}

# ── Post-run verification ──────────────────────────────────────────────────
echo ""
echo "==================================================================="
echo "Golden-test verification — Mg_2025-12"
echo "==================================================================="

# 1. Verify all article PDFs against their declared checksums
echo -n "  [1/3] sha256sum -c … "
(cd "$EXPORT_PATH" && sha256sum -c checksums.sha256 >/dev/null) \
    && echo "[OK]" \
    || { echo "[FAILED]" >&2; exit 1; }

# 2. Compare checksums.sha256 with golden (validates article PDF identity)
echo -n "  [2/3] checksums vs golden … "
if diff <(sort "$GOLDEN_EXPORT/checksums.sha256") <(sort "$EXPORT_PATH/checksums.sha256") >/dev/null; then
    echo "[OK]"
else
    echo "[FAILED]" >&2
    diff "$GOLDEN_EXPORT/checksums.sha256" "$EXPORT_PATH/checksums.sha256" >&2 || true
    exit 1
fi

# 3. Normalized manifest diff
#    Strips all per-run timestamp fields before comparing:
#      .export_path, .export_id, .export_timestamp_utc   — top-level
#      .articles[].export_path                           — per-article
#    Remaining fields (article_id, sha256, filename, bytes, material_kind …)
#    are compared after key-sorting for a stable diff.
echo -n "  [3/3] manifest (normalized) … "
GOLDEN_MANIFEST=$(resolve_manifest "$GOLDEN_EXPORT")
NEW_MANIFEST=$(resolve_manifest "$EXPORT_PATH")
_JQ_STRIP='del(.export_path, .export_id, .export_timestamp_utc, .articles[].export_path)'
if diff \
    <(jq "$_JQ_STRIP" "$GOLDEN_MANIFEST" | jq -S .) \
    <(jq "$_JQ_STRIP" "$NEW_MANIFEST"    | jq -S .) \
    >/dev/null; then
    echo "[OK]"
else
    echo "[FAILED]" >&2
    diff \
        <(jq "$_JQ_STRIP" "$GOLDEN_MANIFEST" | jq -S .) \
        <(jq "$_JQ_STRIP" "$NEW_MANIFEST"    | jq -S .) \
        >&2 || true
    exit 1
fi

# ── Show export structure ──────────────────────────────────────────────────
echo ""
echo "  Export structure:"
tree -L 2 "$EXPORT_PATH" 2>/dev/null || ls -lR "$EXPORT_PATH"

echo ""
echo "==================================================================="
echo "[OK] Golden test PASSED — Mg_2025-12"
echo "==================================================================="
