#!/usr/bin/env python3
"""
OutputValidator v1.0.0 — финальная валидация OutputBuilder exports.

Проверяет:
- T=L=E invariant (total_articles == len(articles) == count(PDFs))
- Export structure (articles/, manifest/, checksums.sha256, README.md)
- Filename compliance (FilenameGenerationPolicy v_1_0)
- SHA256 checksums (3-way verification)
- Manifest consistency

Usage:
    cat output_builder_result.json | python validator.py

Exit codes:
    0: success
    10: invalid_input
    30: verification_failed
    50: internal_error
"""

import sys
import json
import hashlib
import re
from pathlib import Path
from typing import Dict, List, Any, Optional

COMPONENT = "OutputValidator"
VERSION = "1.0.0"

# Exit codes (TechSpec v_2_6 §9)
EXIT_SUCCESS = 0
EXIT_INVALID_INPUT = 10
EXIT_VERIFICATION_FAILED = 30
EXIT_INTERNAL_ERROR = 50


def _error_exit(exit_code: int, code: str, message: str, details: Optional[Dict[str, Any]] = None):
    """Output structured error envelope and exit."""
    error_obj = {
        "code": code,
        "message": message
    }
    if details:
        error_obj["details"] = details

    envelope = {
        "status": "error",
        "component": COMPONENT,
        "version": VERSION,
        "data": None,
        "error": error_obj
    }

    print(json.dumps(envelope, indent=2, ensure_ascii=False))
    sys.exit(exit_code)


def _validate_input_envelope(raw: Any) -> Dict[str, Any]:
    """
    Validate input and apply unwrap pattern.

    TechSpec v_2_6: Accept both envelope and raw data formats.
    """
    if not isinstance(raw, dict):
        _error_exit(
            EXIT_INVALID_INPUT,
            "invalid_input_format",
            "Input must be JSON object",
            {"received_type": type(raw).__name__}
        )

    # Unwrap pattern
    payload = raw.get("data", raw) if "status" in raw else raw

    # Required fields
    required = ["issue_id", "export_path", "total_articles", "articles"]
    missing = [f for f in required if f not in payload]
    if missing:
        _error_exit(
            EXIT_INVALID_INPUT,
            "missing_required_fields",
            "Input missing required fields",
            {"missing_fields": missing}
        )

    return payload


def _validate_export_structure(export_path: str):
    """
    Validate export directory structure.

    Required:
    - articles/
    - manifest/
    - checksums.sha256
    - README.md
    """
    base = Path(export_path)

    if not base.exists():
        _error_exit(
            EXIT_VERIFICATION_FAILED,
            "export_path_not_found",
            f"Export path does not exist: {export_path}"
        )

    if not base.is_dir():
        _error_exit(
            EXIT_VERIFICATION_FAILED,
            "export_path_not_directory",
            f"Export path is not a directory: {export_path}"
        )

    required_paths = {
        "articles": base / "articles",
        "manifest": base / "manifest",
        "checksums.sha256": base / "checksums.sha256",
        "README.md": base / "README.md"
    }

    missing = []
    for name, path in required_paths.items():
        if not path.exists():
            missing.append(name)

    if missing:
        _error_exit(
            EXIT_VERIFICATION_FAILED,
            "incomplete_export_structure",
            "Export directory missing required files/folders",
            {"missing": missing, "export_path": export_path}
        )


def _validate_t_l_e_invariant(data: Dict[str, Any], article_files: List[Path]):
    """
    Enforce T=L=E invariant (TechSpec v_2_6 §2 Rule 6).

    T = total_articles (count in JSON)
    L = len(articles) (list length in JSON)
    E = count of PDFs in articles/ directory

    Must satisfy: T == L == E
    """
    T = data["total_articles"]
    L = len(data["articles"])
    E = len(article_files)

    if not (T == L == E):
        _error_exit(
            EXIT_VERIFICATION_FAILED,
            "t_l_e_invariant_violation",
            "T=L=E invariant violated",
            {
                "T_total_articles": T,
                "L_articles_list_length": L,
                "E_pdf_files_count": E,
                "invariant": "T == L == E",
                "satisfied": False
            }
        )


def _validate_filename_policy(article: Dict[str, Any]):
    """
    Validate filename against FilenameGenerationPolicy v_1_0.

    Research format: {IssuePrefix}_{PPP-PPP}_{Surname}.pdf
    Service format:  {IssuePrefix}_{PPP-PPP}_{ServiceSuffix}.pdf

    ServiceSuffix examples: Contents, Editorial, Digest
    """
    filename = article.get("filename")
    material_kind = article.get("material_kind")

    if not filename:
        _error_exit(
            EXIT_VERIFICATION_FAILED,
            "missing_filename",
            "Article missing filename field",
            {"article": article}
        )

    # Research pattern: Mg_2025-12_005-014_Ivanov.pdf
    research_pattern = r'^[A-Za-z]+_\d{4}-\d{2}_\d{3}-\d{3}_[A-Z][a-z]+\.pdf$'

    # Service pattern: Mg_2025-12_001-004_Contents.pdf
    service_pattern = r'^[A-Za-z]+_\d{4}-\d{2}_\d{3}-\d{3}_(Contents|Editorial|Digest)\.pdf$'

    if material_kind == "research":
        if not re.match(research_pattern, filename):
            _error_exit(
                EXIT_VERIFICATION_FAILED,
                "invalid_research_filename",
                "Research article filename does not match policy",
                {
                    "filename": filename,
                    "material_kind": material_kind,
                    "expected_pattern": "IssuePrefix_YYYY-MM_PPP-PPP_Surname.pdf"
                }
            )

    elif material_kind in ["contents", "editorial", "digest"]:
        if not re.match(service_pattern, filename):
            _error_exit(
                EXIT_VERIFICATION_FAILED,
                "invalid_service_filename",
                "Service material filename does not match policy",
                {
                    "filename": filename,
                    "material_kind": material_kind,
                    "expected_pattern": "IssuePrefix_YYYY-MM_PPP-PPP_ServiceSuffix.pdf"
                }
            )

    else:
        _error_exit(
            EXIT_VERIFICATION_FAILED,
            "unknown_material_kind",
            f"Unknown material_kind: {material_kind}",
            {"article": article}
        )


def _compute_sha256(file_path: Path) -> str:
    """Compute SHA256 checksum (chunked reading for large files)."""
    sha256_hash = hashlib.sha256()
    with open(file_path, "rb") as f:
        for chunk in iter(lambda: f.read(8192), b""):
            sha256_hash.update(chunk)
    return sha256_hash.hexdigest()


def _validate_checksums(articles: List[Dict], checksums_path: Path, export_path: Path):
    """
    3-way SHA256 checksum verification:
    1. Compute SHA256 from actual PDF files
    2. Compare with checksums.sha256 file
    3. Compare with manifest field
    4. Compare with stdin article field
    """
    # Load checksums.sha256 file
    checksums_file_map = {}
    with open(checksums_path, "r") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            parts = line.split(maxsplit=1)
            if len(parts) != 2:
                _error_exit(
                    EXIT_VERIFICATION_FAILED,
                    "invalid_checksums_file_format",
                    f"Invalid line in checksums.sha256: {line}"
                )
            checksum, filename = parts
            checksums_file_map[filename] = checksum

    # Validate each article
    for article in articles:
        filename = article["filename"]
        pdf_path = export_path / "articles" / filename

        if not pdf_path.exists():
            _error_exit(
                EXIT_VERIFICATION_FAILED,
                "missing_pdf_file",
                f"PDF file not found in articles/",
                {"filename": filename}
            )

        # Compute actual SHA256
        computed = _compute_sha256(pdf_path)

        # Get expected checksums from different sources
        from_stdin = article.get("sha256_checksum")
        from_file = checksums_file_map.get(filename)
        from_manifest = article.get("manifest", {}).get("sha256_checksum")

        # 3-way comparison
        mismatches = []

        if from_stdin and computed != from_stdin:
            mismatches.append(f"stdin: {from_stdin}")

        if from_file and computed != from_file:
            mismatches.append(f"checksums.sha256: {from_file}")

        if from_manifest and computed != from_manifest:
            mismatches.append(f"manifest: {from_manifest}")

        if mismatches:
            _error_exit(
                EXIT_VERIFICATION_FAILED,
                "checksum_mismatch",
                f"SHA256 mismatch for {filename}",
                {
                    "filename": filename,
                    "computed": computed,
                    "mismatches": mismatches
                }
            )


def main():
    """Main validation orchestration."""
    try:
        # Read stdin
        raw_input = sys.stdin.read()
        if not raw_input.strip():
            _error_exit(
                EXIT_INVALID_INPUT,
                "empty_stdin",
                "No input received on stdin"
            )

        try:
            raw = json.loads(raw_input)
        except json.JSONDecodeError as e:
            _error_exit(
                EXIT_INVALID_INPUT,
                "invalid_json",
                "Failed to parse JSON from stdin",
                {"parse_error": str(e)}
            )

        # Step 1: Validate input envelope (unwrap pattern)
        data = _validate_input_envelope(raw)

        export_path = Path(data["export_path"])

        # Step 2: Validate export structure
        _validate_export_structure(export_path)

        # Step 3: Collect article files
        articles_dir = export_path / "articles"
        article_files = sorted(articles_dir.glob("*.pdf"))

        # Step 4: Validate T=L=E invariant
        _validate_t_l_e_invariant(data, article_files)

        # Step 5: Validate filename policy
        for article in data["articles"]:
            _validate_filename_policy(article)

        # Step 6: Validate checksums (3-way)
        checksums_path = export_path / "checksums.sha256"
        _validate_checksums(data["articles"], checksums_path, export_path)

        # Success envelope
        success_envelope = {
            "status": "success",
            "component": COMPONENT,
            "version": VERSION,
            "data": {
                "issue_id": data["issue_id"],
                "export_path": str(export_path),
                "total_articles": data["total_articles"],
                "validation_summary": {
                    "t_l_e_invariant": "satisfied",
                    "export_structure": "valid",
                    "filename_policy": "compliant",
                    "checksums": "verified"
                }
            },
            "error": None
        }

        print(json.dumps(success_envelope, indent=2, ensure_ascii=False))
        sys.exit(EXIT_SUCCESS)

    except Exception as e:
        _error_exit(
            EXIT_INTERNAL_ERROR,
            "internal_error",
            "Unexpected error during validation",
            {"exception": str(e), "type": type(e).__name__}
        )


if __name__ == "__main__":
    main()
