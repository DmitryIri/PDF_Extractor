#!/usr/bin/env python3
"""
Unit tests for OutputValidator v1.0.0

Tests validation logic with mocked filesystem.
"""

import unittest
import json
import sys
from pathlib import Path
from unittest.mock import patch, mock_open, MagicMock
from io import StringIO

# Add agents directory to path
sys.path.insert(0, str(Path(__file__).parent.parent / "agents" / "output_validator"))
import validator


class TestUnwrapPattern(unittest.TestCase):
    """Test unwrap pattern for envelope/raw data acceptance."""

    def test_unwrap_pattern_envelope_format(self):
        """Accept envelope with data field."""
        raw = {
            "status": "success",
            "component": "OutputBuilder",
            "version": "1.0.0",
            "data": {
                "issue_id": "mg_2025_12",
                "export_path": "/srv/pdf-extractor/exports/mg_2025_12/test",
                "total_articles": 1,
                "articles": [{"filename": "test.pdf"}]
            }
        }

        result = validator._validate_input_envelope(raw)

        self.assertEqual(result["issue_id"], "mg_2025_12")
        self.assertEqual(result["total_articles"], 1)

    def test_unwrap_pattern_raw_format(self):
        """Accept raw data without envelope."""
        raw = {
            "issue_id": "mg_2025_12",
            "export_path": "/srv/pdf-extractor/exports/mg_2025_12/test",
            "total_articles": 1,
            "articles": [{"filename": "test.pdf"}]
        }

        result = validator._validate_input_envelope(raw)

        self.assertEqual(result["issue_id"], "mg_2025_12")
        self.assertEqual(result["total_articles"], 1)

    def test_unwrap_pattern_missing_required_fields(self):
        """Fail when required fields missing."""
        raw = {
            "issue_id": "mg_2025_12"
            # Missing: export_path, total_articles, articles
        }

        with self.assertRaises(SystemExit) as cm:
            validator._validate_input_envelope(raw)

        self.assertEqual(cm.exception.code, validator.EXIT_INVALID_INPUT)


class TestTLEInvariant(unittest.TestCase):
    """Test T=L=E invariant enforcement."""

    def test_t_l_e_invariant_satisfied(self):
        """Pass when T == L == E."""
        data = {
            "total_articles": 3,
            "articles": [
                {"filename": "a.pdf"},
                {"filename": "b.pdf"},
                {"filename": "c.pdf"}
            ]
        }

        article_files = [
            Path("a.pdf"),
            Path("b.pdf"),
            Path("c.pdf")
        ]

        # Should not raise
        validator._validate_t_l_e_invariant(data, article_files)

    def test_t_l_e_invariant_violated_t_ne_l(self):
        """Fail when T ≠ L."""
        data = {
            "total_articles": 5,  # T = 5
            "articles": [  # L = 3
                {"filename": "a.pdf"},
                {"filename": "b.pdf"},
                {"filename": "c.pdf"}
            ]
        }

        article_files = [  # E = 3
            Path("a.pdf"),
            Path("b.pdf"),
            Path("c.pdf")
        ]

        with self.assertRaises(SystemExit) as cm:
            validator._validate_t_l_e_invariant(data, article_files)

        self.assertEqual(cm.exception.code, validator.EXIT_VERIFICATION_FAILED)

    def test_t_l_e_invariant_violated_l_ne_e(self):
        """Fail when L ≠ E."""
        data = {
            "total_articles": 3,  # T = 3
            "articles": [  # L = 3
                {"filename": "a.pdf"},
                {"filename": "b.pdf"},
                {"filename": "c.pdf"}
            ]
        }

        article_files = [  # E = 2
            Path("a.pdf"),
            Path("b.pdf")
        ]

        with self.assertRaises(SystemExit) as cm:
            validator._validate_t_l_e_invariant(data, article_files)

        self.assertEqual(cm.exception.code, validator.EXIT_VERIFICATION_FAILED)

    def test_t_l_e_invariant_zero_articles(self):
        """Pass when T == L == E == 0."""
        data = {
            "total_articles": 0,
            "articles": []
        }

        article_files = []

        # Should not raise
        validator._validate_t_l_e_invariant(data, article_files)


class TestFilenamePolicyValidation(unittest.TestCase):
    """Test filename policy compliance (FilenameGenerationPolicy v_1_0)."""

    def test_filename_policy_research_valid(self):
        """Research filename matches pattern."""
        article = {
            "filename": "Mg_2025-12_005-014_Ivanov.pdf",
            "material_kind": "research"
        }

        # Should not raise
        validator._validate_filename_policy(article)

    def test_filename_policy_service_contents_valid(self):
        """Service filename (Contents) matches pattern."""
        article = {
            "filename": "Mg_2025-12_001-004_Contents.pdf",
            "material_kind": "contents"
        }

        # Should not raise
        validator._validate_filename_policy(article)

    def test_filename_policy_service_editorial_valid(self):
        """Service filename (Editorial) matches pattern."""
        article = {
            "filename": "Mg_2025-12_002-003_Editorial.pdf",
            "material_kind": "editorial"
        }

        # Should not raise
        validator._validate_filename_policy(article)

    def test_filename_policy_research_invalid(self):
        """Research filename fails validation."""
        article = {
            "filename": "Mg_2025-12_005-014_IVANOV.pdf",  # Surname must be capitalized (Title case)
            "material_kind": "research"
        }

        with self.assertRaises(SystemExit) as cm:
            validator._validate_filename_policy(article)

        self.assertEqual(cm.exception.code, validator.EXIT_VERIFICATION_FAILED)

    def test_filename_policy_service_invalid_suffix(self):
        """Service filename with invalid suffix fails."""
        article = {
            "filename": "Mg_2025-12_001-004_FrontMatter.pdf",  # Invalid suffix
            "material_kind": "contents"
        }

        with self.assertRaises(SystemExit) as cm:
            validator._validate_filename_policy(article)

        self.assertEqual(cm.exception.code, validator.EXIT_VERIFICATION_FAILED)

    def test_filename_policy_unknown_material_kind(self):
        """Unknown material_kind fails."""
        article = {
            "filename": "Mg_2025-12_005-014_Test.pdf",
            "material_kind": "unknown_type"
        }

        with self.assertRaises(SystemExit) as cm:
            validator._validate_filename_policy(article)

        self.assertEqual(cm.exception.code, validator.EXIT_VERIFICATION_FAILED)

    def test_filename_policy_missing_filename(self):
        """Missing filename field fails."""
        article = {
            "material_kind": "research"
            # Missing: filename
        }

        with self.assertRaises(SystemExit) as cm:
            validator._validate_filename_policy(article)

        self.assertEqual(cm.exception.code, validator.EXIT_VERIFICATION_FAILED)


class TestChecksumValidation(unittest.TestCase):
    """Test 3-way SHA256 checksum verification."""

    @patch('validator.Path.exists')
    @patch('validator._compute_sha256')
    @patch('builtins.open', new_callable=mock_open, read_data="abc123 test.pdf\n")
    def test_checksum_3way_match(self, mock_file, mock_compute, mock_exists):
        """All 3 checksums match."""
        mock_exists.return_value = True
        mock_compute.return_value = "abc123"

        articles = [
            {
                "filename": "test.pdf",
                "sha256_checksum": "abc123",
                "manifest": {
                    "sha256_checksum": "abc123"
                }
            }
        ]

        checksums_path = Path("/test/checksums.sha256")
        export_path = Path("/test")

        # Should not raise
        validator._validate_checksums(articles, checksums_path, export_path)

    @patch('validator.Path.exists')
    @patch('validator._compute_sha256')
    @patch('builtins.open', new_callable=mock_open, read_data="abc123 test.pdf\n")
    def test_checksum_mismatch_stdin(self, mock_file, mock_compute, mock_exists):
        """Stdin checksum mismatch detected."""
        mock_exists.return_value = True
        mock_compute.return_value = "computed_hash"

        articles = [
            {
                "filename": "test.pdf",
                "sha256_checksum": "wrong_hash",  # Mismatch
                "manifest": {
                    "sha256_checksum": "computed_hash"
                }
            }
        ]

        checksums_path = Path("/test/checksums.sha256")
        export_path = Path("/test")

        with self.assertRaises(SystemExit) as cm:
            validator._validate_checksums(articles, checksums_path, export_path)

        self.assertEqual(cm.exception.code, validator.EXIT_VERIFICATION_FAILED)

    @patch('validator.Path.exists')
    @patch('validator._compute_sha256')
    @patch('builtins.open', new_callable=mock_open, read_data="wrong_hash test.pdf\n")
    def test_checksum_mismatch_file(self, mock_file, mock_compute, mock_exists):
        """checksums.sha256 file mismatch detected."""
        mock_exists.return_value = True
        mock_compute.return_value = "computed_hash"

        articles = [
            {
                "filename": "test.pdf",
                "sha256_checksum": "computed_hash",
                "manifest": {
                    "sha256_checksum": "computed_hash"
                }
            }
        ]

        checksums_path = Path("/test/checksums.sha256")
        export_path = Path("/test")

        with self.assertRaises(SystemExit) as cm:
            validator._validate_checksums(articles, checksums_path, export_path)

        self.assertEqual(cm.exception.code, validator.EXIT_VERIFICATION_FAILED)


class TestExportStructureValidation(unittest.TestCase):
    """Test export directory structure validation."""

    def test_missing_export_structure(self):
        """Missing articles/ detected."""
        # Create mock Path objects
        mock_base = MagicMock()
        mock_base.exists.return_value = True
        mock_base.is_dir.return_value = True

        # Mock child paths
        mock_articles = MagicMock()
        mock_articles.exists.return_value = False  # Missing!

        mock_manifest = MagicMock()
        mock_manifest.exists.return_value = True

        mock_checksums = MagicMock()
        mock_checksums.exists.return_value = True

        mock_readme = MagicMock()
        mock_readme.exists.return_value = True

        # Setup __truediv__ to return appropriate mocks
        def truediv_side_effect(self, name):
            if name == "articles":
                return mock_articles
            elif name == "manifest":
                return mock_manifest
            elif name == "checksums.sha256":
                return mock_checksums
            elif name == "README.md":
                return mock_readme
            return MagicMock()

        mock_base.__truediv__ = MagicMock(side_effect=lambda name: truediv_side_effect(mock_base, name))

        with patch('validator.Path', return_value=mock_base):
            export_path = "/test/export"

            with self.assertRaises(SystemExit) as cm:
                validator._validate_export_structure(export_path)

            self.assertEqual(cm.exception.code, validator.EXIT_VERIFICATION_FAILED)

    @patch('validator.Path.exists')
    def test_export_path_not_found(self, mock_exists):
        """Export path does not exist."""
        mock_exists.return_value = False

        export_path = "/nonexistent/path"

        with self.assertRaises(SystemExit) as cm:
            validator._validate_export_structure(export_path)

        self.assertEqual(cm.exception.code, validator.EXIT_VERIFICATION_FAILED)


class TestInputValidation(unittest.TestCase):
    """Test input validation edge cases."""

    def test_empty_stdin(self):
        """Empty stdin handled gracefully."""
        raw = ""

        # This would be tested in main() function
        # For unit test, we check _validate_input_envelope with None
        with self.assertRaises(SystemExit):
            validator._validate_input_envelope(None)

    def test_invalid_json_type(self):
        """Non-dict JSON fails."""
        raw = ["array", "not", "dict"]

        with self.assertRaises(SystemExit) as cm:
            validator._validate_input_envelope(raw)

        self.assertEqual(cm.exception.code, validator.EXIT_INVALID_INPUT)


if __name__ == "__main__":
    unittest.main()
