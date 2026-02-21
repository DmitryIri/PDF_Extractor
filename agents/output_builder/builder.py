#!/usr/bin/env python3
# PDF Extractor — OutputBuilder
# Build final export structure on filesystem
#
# Contract:
# - stdin: JSON envelope (or raw) with VerifiedArticleManifest from MetadataVerifier
# - stdout (fd1): JSON envelope with export manifest for OutputValidator
# - stderr (fd2): logs only, no JSON
# - exit codes: 0=success, 10=invalid_input, 40=build_failed, 50=internal_error
#
# Export structure (per session_closure_log_2026_01_23_v_1_2.md §3.3):
#   /srv/pdf-extractor/exports/{JournalCode}/{YYYY}/{IssuePrefix}/exports/{export_id}/
#     ├── articles/{expected_filename}.pdf
#     ├── manifest/export_manifest.json
#     ├── checksums.sha256
#     └── README.md

from __future__ import annotations

import hashlib
import json
import os
import re
import shutil
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional

COMPONENT = "OutputBuilder"
VERSION = "1.2.0"  # Add info material_kind support

# Export root directory (canonical per project design)
EXPORT_ROOT = Path("/srv/pdf-extractor/exports")


def _error_exit(exit_code: int, code: str, message: str, details: Optional[Dict[str, Any]] = None) -> None:
    """Emit error envelope to stdout and exit."""
    out = {
        "status": "error",
        "component": COMPONENT,
        "version": VERSION,
        "data": None,
        "error": {"exit_code": exit_code, "code": code, "message": message, "details": details or {}},
    }
    json_bytes = (json.dumps(out, ensure_ascii=False) + "\n").encode("utf-8")
    os.write(1, json_bytes)
    raise SystemExit(exit_code)


def _extract_year_from_issue_prefix(issue_prefix: str) -> str:
    """Extract year from issue_prefix.

    Expected format: {JournalCode}_{YYYY}-{MM}
    Example: Mg_2025-12 → 2025
    """
    match = re.match(r'^[A-Za-z]{2}_(\d{4})-\d{2}$', issue_prefix)
    if not match:
        _error_exit(10, "invalid_input",
                    f"issue_prefix '{issue_prefix}' does not match expected format {{JournalCode}}_{{YYYY}}-{{MM}}")
    return match.group(1)


def _generate_export_id() -> str:
    """Generate deterministic export_id from current UTC time.

    Format: YYYY_MM_DD__HH_MM_SS
    Example: 2026_01_26__14_30_00
    """
    now = datetime.now(timezone.utc)
    return now.strftime("%Y_%m_%d__%H_%M_%S")


def _compute_sha256(file_path: Path) -> str:
    """Compute SHA256 hash of file."""
    sha256 = hashlib.sha256()
    with open(file_path, "rb") as f:
        while chunk := f.read(8192):
            sha256.update(chunk)
    return sha256.hexdigest()


def _validate_material_kind_filename(article: Dict[str, Any]) -> None:
    """
    Validate that material_kind matches expected_filename pattern.

    Rules:
    - contents → filename ends with _Contents.pdf
    - editorial → filename ends with _Editorial.pdf
    - digest → filename ends with _Digest.pdf
    - research → filename does NOT end with service suffixes, must have surname
    """
    material_kind = article.get("material_kind")
    expected_filename = article.get("expected_filename", "")
    article_id = article.get("article_id", "unknown")

    if not material_kind:
        _error_exit(40, "build_failed",
                    f"Article {article_id}: missing material_kind field")

    # Service suffix patterns
    service_suffixes = ["_Contents.pdf", "_Editorial.pdf", "_Digest.pdf", "_Info.pdf"]

    if material_kind == "contents":
        if not expected_filename.endswith("_Contents.pdf"):
            _error_exit(40, "build_failed",
                        f"Article {article_id}: material_kind=contents but filename doesn't end with _Contents.pdf: {expected_filename}")

    elif material_kind == "editorial":
        if not expected_filename.endswith("_Editorial.pdf"):
            _error_exit(40, "build_failed",
                        f"Article {article_id}: material_kind=editorial but filename doesn't end with _Editorial.pdf: {expected_filename}")

    elif material_kind == "digest":
        if not expected_filename.endswith("_Digest.pdf"):
            _error_exit(40, "build_failed",
                        f"Article {article_id}: material_kind=digest but filename doesn't end with _Digest.pdf: {expected_filename}")

    elif material_kind == "info":
        if not expected_filename.endswith("_Info.pdf"):
            _error_exit(40, "build_failed",
                        f"Article {article_id}: material_kind=info but filename doesn't end with _Info.pdf: {expected_filename}")

    elif material_kind == "research":
        # Research articles must NOT use service suffixes
        for suffix in service_suffixes:
            if expected_filename.endswith(suffix):
                _error_exit(40, "build_failed",
                            f"Article {article_id}: material_kind=research but filename uses service suffix {suffix}: {expected_filename}")

        # Research must have first_author_surname
        if "first_author_surname" not in article or not article["first_author_surname"]:
            _error_exit(40, "build_failed",
                        f"Article {article_id}: material_kind=research but missing first_author_surname")

    else:
        _error_exit(40, "build_failed",
                    f"Article {article_id}: invalid material_kind '{material_kind}'")


def _build_export_structure(
    journal_code: str,
    issue_prefix: str,
    year: str,
    export_id: str,
    articles: List[Dict[str, Any]],
    issue_id: Optional[str] = None
) -> Dict[str, Any]:
    """Build export directory structure and copy article PDFs.

    Returns export manifest dict.
    """
    # Build export path
    export_base = EXPORT_ROOT / journal_code / year / issue_prefix / "exports"
    export_path = export_base / export_id
    export_tmp = export_base / f"{export_id}.tmp"

    # Ensure export_base exists
    try:
        export_base.mkdir(parents=True, exist_ok=True)
    except Exception as e:
        _error_exit(40, "build_failed", f"Cannot create export base directory: {e}",
                    {"export_base": str(export_base), "exception": str(e)})

    # Check if export already exists
    if export_path.exists():
        _error_exit(40, "build_failed", f"Export already exists: {export_path}",
                    {"export_path": str(export_path)})

    # Create tmp directory
    try:
        export_tmp.mkdir(parents=False, exist_ok=False)
        (export_tmp / "articles").mkdir(parents=False)
        (export_tmp / "manifest").mkdir(parents=False)
    except Exception as e:
        _error_exit(40, "build_failed", f"Cannot create tmp export structure: {e}",
                    {"export_tmp": str(export_tmp), "exception": str(e)})

    # Copy article PDFs and build manifest entries
    exported_articles = []
    checksums = []

    for article in articles:
        # Validate material_kind matches filename pattern
        _validate_material_kind_filename(article)

        article_id = article["article_id"]
        expected_filename = article["expected_filename"]
        material_kind = article["material_kind"]
        splitter_output = article["splitter_output"]
        source_path = Path(splitter_output["path"])

        # Destination path
        dest_path = export_tmp / "articles" / expected_filename

        # Verify source exists
        if not source_path.exists():
            # Cleanup tmp on error
            shutil.rmtree(export_tmp, ignore_errors=True)
            _error_exit(40, "build_failed",
                        f"Article {article_id}: source PDF does not exist: {source_path}",
                        {"article_id": article_id, "source_path": str(source_path)})

        # Copy file
        try:
            shutil.copy2(source_path, dest_path)
        except Exception as e:
            # Cleanup tmp on error
            shutil.rmtree(export_tmp, ignore_errors=True)
            _error_exit(40, "build_failed",
                        f"Article {article_id}: failed to copy PDF: {e}",
                        {"article_id": article_id, "source": str(source_path),
                         "dest": str(dest_path), "exception": str(e)})

        # Verify copied file
        dest_size = dest_path.stat().st_size
        dest_sha256 = _compute_sha256(dest_path)

        # Verify size and checksum match
        expected_size = splitter_output["bytes"]
        expected_sha256 = splitter_output["sha256"]

        if dest_size != expected_size:
            shutil.rmtree(export_tmp, ignore_errors=True)
            _error_exit(40, "build_failed",
                        f"Article {article_id}: size mismatch after copy (expected {expected_size}, got {dest_size})",
                        {"article_id": article_id, "expected_size": expected_size, "actual_size": dest_size})

        if dest_sha256 != expected_sha256:
            shutil.rmtree(export_tmp, ignore_errors=True)
            _error_exit(40, "build_failed",
                        f"Article {article_id}: SHA256 mismatch after copy",
                        {"article_id": article_id, "expected_sha256": expected_sha256, "actual_sha256": dest_sha256})

        # Build exported article entry
        # Use relative path from export root for portability
        relative_path = dest_path.relative_to(export_tmp)
        final_relative_path = export_path / relative_path

        exported_article = {
            "article_id": article_id,
            "filename": expected_filename,  # OutputValidator expects "filename"
            "expected_filename": expected_filename,  # Keep for backward compatibility
            "material_kind": material_kind,
            "export_path": str(final_relative_path),
            "bytes": dest_size,
            "sha256": dest_sha256,
            "from_page": article["from_page"],
            "to_page": article["to_page"]
        }

        # Add surname fields for research articles
        if material_kind == "research":
            exported_article["first_author_surname"] = article.get("first_author_surname")
            exported_article["first_author_surname_source"] = article.get("first_author_surname_source")

        exported_articles.append(exported_article)

        # Add to checksums list (SHA256SUMS format: {hash}  {filename})
        checksums.append(f"{dest_sha256}  articles/{expected_filename}")

    # Generate manifest/export_manifest.json
    export_manifest_data = {
        "export_id": export_id,
        "journal_code": journal_code,
        "issue_prefix": issue_prefix,
        "year": year,
        "total_articles": len(exported_articles),
        "articles": exported_articles,
        "export_timestamp_utc": datetime.now(timezone.utc).isoformat()
    }

    manifest_path = export_tmp / "manifest" / "export_manifest.json"
    try:
        with open(manifest_path, "w", encoding="utf-8") as f:
            json.dump(export_manifest_data, f, ensure_ascii=False, indent=2, sort_keys=True)
            f.write("\n")
    except Exception as e:
        shutil.rmtree(export_tmp, ignore_errors=True)
        _error_exit(40, "build_failed", f"Cannot write export manifest: {e}",
                    {"manifest_path": str(manifest_path), "exception": str(e)})

    # Generate checksums.sha256
    checksums_path = export_tmp / "checksums.sha256"
    try:
        with open(checksums_path, "w", encoding="utf-8") as f:
            f.write("\n".join(checksums))
            f.write("\n")
    except Exception as e:
        shutil.rmtree(export_tmp, ignore_errors=True)
        _error_exit(40, "build_failed", f"Cannot write checksums file: {e}",
                    {"checksums_path": str(checksums_path), "exception": str(e)})

    # Generate README.md
    readme_path = export_tmp / "README.md"
    readme_content = f"""# PDF Extractor Export

**Export ID:** {export_id}
**Journal:** {journal_code}
**Issue:** {issue_prefix}
**Year:** {year}
**Total Articles:** {len(exported_articles)}
**Export Timestamp (UTC):** {datetime.now(timezone.utc).isoformat()}

## Contents

- `articles/` — Extracted article PDFs
- `manifest/export_manifest.json` — Export metadata
- `checksums.sha256` — SHA256 checksums for all article PDFs

## Verification

To verify integrity of article PDFs:

```bash
cd {export_path}
sha256sum -c checksums.sha256
```

All files should report: OK

---

Generated by PDF Extractor v{VERSION}
"""

    try:
        with open(readme_path, "w", encoding="utf-8") as f:
            f.write(readme_content)
    except Exception as e:
        shutil.rmtree(export_tmp, ignore_errors=True)
        _error_exit(40, "build_failed", f"Cannot write README: {e}",
                    {"readme_path": str(readme_path), "exception": str(e)})

    # Atomic rename: {export_id}.tmp → {export_id}
    try:
        export_tmp.rename(export_path)
    except Exception as e:
        # Cleanup tmp on error
        shutil.rmtree(export_tmp, ignore_errors=True)
        _error_exit(40, "build_failed", f"Cannot finalize export (atomic rename failed): {e}",
                    {"export_tmp": str(export_tmp), "export_path": str(export_path), "exception": str(e)})

    # Build result manifest
    result = {
        "export_id": export_id,
        "journal_code": journal_code,
        "issue_prefix": issue_prefix,
        "year": year,
        "export_path": str(export_path),
        "total_articles": len(exported_articles),
        "articles": exported_articles,
        "manifest_path": str(export_path / "manifest" / "export_manifest.json"),
        "checksums_path": str(export_path / "checksums.sha256"),
        "readme_path": str(export_path / "README.md")
    }

    # Pass through issue_id if provided (for OutputValidator)
    if issue_id:
        result["issue_id"] = issue_id

    return result


def main() -> None:
    # Read stdin
    try:
        raw = json.load(sys.stdin)
    except Exception as e:
        _error_exit(10, "invalid_input", f"Invalid JSON on stdin: {e}")

    # Unwrap envelope (TechSpec v_2_5 §5)
    payload = raw.get("data", raw) if isinstance(raw, dict) else raw

    # Validate required top-level fields
    try:
        issue_id = payload.get("issue_id")  # Optional: pass through for OutputValidator
        journal_code = payload.get("journal_code")
        issue_prefix = payload.get("issue_prefix")
        articles = payload.get("articles")

        if not journal_code or not isinstance(journal_code, str):
            raise ValueError("journal_code is required and must be a string")
        if not issue_prefix or not isinstance(issue_prefix, str):
            raise ValueError("issue_prefix is required and must be a string")
        if articles is None or not isinstance(articles, list):
            raise ValueError("articles is required and must be a list")

        # Validate journal_code (exactly 2 letters)
        if len(journal_code) != 2 or not journal_code.isalpha():
            raise ValueError(f"journal_code must be exactly 2 letters: {journal_code}")

    except (KeyError, ValueError) as e:
        _error_exit(10, "invalid_input", str(e))

    # Extract year from issue_prefix
    year = _extract_year_from_issue_prefix(issue_prefix)

    # Generate export_id
    export_id = _generate_export_id()

    # Build export structure
    export_manifest = _build_export_structure(journal_code, issue_prefix, year, export_id, articles, issue_id)

    # Success envelope
    out = {
        "status": "success",
        "component": COMPONENT,
        "version": VERSION,
        "data": export_manifest,
        "error": None
    }

    # Emit JSON to stdout (deterministic: sort_keys, separators)
    json_bytes = (json.dumps(out, ensure_ascii=False, sort_keys=True, separators=(',', ':')) + "\n").encode("utf-8")
    os.write(1, json_bytes)


if __name__ == "__main__":
    try:
        main()
    except SystemExit:
        raise
    except Exception as e:
        _error_exit(50, "internal_error", f"Unexpected error: {e}", {"exception": str(e)})
