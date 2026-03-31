"""Unit tests — MetadataExtractor._pick_ru_authors / _pick_en_authors.

Tests running-header exclusion, positive byline gating, single-initial support,
and regression coverage for previously accepted valid cases.

Root cause addressed (Mh_2026-03):
- Running header "Том 21, № 3" on article start page was selected as ru_authors
  instead of the real author byline, because _pick_ru_authors lacked is_running_header gate.
- Body text fragment "Анализируя труды В.Д. ..." was selected as ru_authors on page 2
  because old logic accepted any text with comma or initials anywhere.
- Foreign single-initial author "Гелприн М." was not detected at all (AUTH_INITIALS_RE
  required 2 initials), causing BoundaryDetector to classify article as editorial.
"""

import os
import sys

import pytest

_REPO_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
sys.path.insert(0, _REPO_ROOT)
sys.path.insert(0, os.path.join(_REPO_ROOT, "agents", "metadata_extractor"))

from extractor import _pick_ru_authors, _pick_en_authors  # noqa: E402


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _candidate(text: str, y0: float, x0: float = 0.0, font_size: float = 10.0) -> dict:
    """Build a minimal text_block candidate dict for _pick_ru/en_authors."""
    return {
        "text": text,
        "bbox": [x0, y0, x0 + 200.0, y0 + 12.0],
        "font_size": font_size,
    }


def _title(text: str, y0: float = 30.0) -> dict:
    return _candidate(text, y0=y0, font_size=14.0)


# ---------------------------------------------------------------------------
# TestPickRuAuthors — running-header exclusion
# ---------------------------------------------------------------------------
class TestPickRuAuthorsRunningHeaderExclusion:
    """Running headers must be skipped even when they appear after the title."""

    def test_skips_tom_header_finds_real_byline(self):
        """Regression: Mh_2026-03 p33 — 'Том 21, № 3' was picked instead of 'Василькова ж.Г.'"""
        title = _title("МЕДИКО-СОЦИАЛЬНЫЕ АСПЕКТЫ", y0=33.0)
        candidates = [
            title,
            _candidate("Том 21, № 3", y0=38.0),        # running header — MUST be skipped
            _candidate("Василькова ж.Г.", y0=55.0),     # real author byline
        ]
        result = _pick_ru_authors(candidates, title)
        assert result is not None
        assert result["text"] == "Василькова ж.Г."

    def test_skips_vol_header_finds_real_byline(self):
        title = _title("ORIGINAL RESEARCH", y0=30.0)
        candidates = [
            title,
            _candidate("Vol. 21, No. 3", y0=35.0),     # running header EN
            _candidate("Плоткин Ф.Б.", y0=50.0),
        ]
        result = _pick_ru_authors(candidates, title)
        assert result is not None
        assert result["text"] == "Плоткин Ф.Б."

    def test_returns_none_when_only_header_present(self):
        title = _title("Some Article Title", y0=30.0)
        candidates = [
            title,
            _candidate("Том 21, № 3", y0=38.0),
        ]
        result = _pick_ru_authors(candidates, title)
        assert result is None


# ---------------------------------------------------------------------------
# TestPickRuAuthors — positive byline gating (body text rejection)
# ---------------------------------------------------------------------------
class TestPickRuAuthorsPositiveGating:
    """Body text containing initials must be rejected; real bylines accepted."""

    def test_rejects_body_text_with_initials_mid_sentence(self):
        """Regression: Mh_2026-03 p34 — 'Анализируя труды В.Д. Менделевича...' was accepted."""
        title = _title("Some body continuation", y0=100.0)
        candidates = [
            title,
            _candidate("Анализируя труды В.Д. Менделевича, следует отметить", y0=110.0),
            _candidate("Брагина Е.Ю.", y0=120.0),   # real byline
        ]
        result = _pick_ru_authors(candidates, title)
        assert result is not None
        assert result["text"] == "Брагина Е.Ю."

    def test_rejects_body_fragment_with_comma(self):
        """Fragment 'ским и другим изменениям, стрессам' must not be accepted."""
        title = _title("Article title", y0=30.0)
        candidates = [
            title,
            _candidate("ским и другим изменениям, стрессам и т.д.", y0=40.0),
            _candidate("Плоткин Ф.Б.", y0=55.0),
        ]
        result = _pick_ru_authors(candidates, title)
        assert result is not None
        assert result["text"] == "Плоткин Ф.Б."

    def test_accepts_multi_author_byline(self):
        """'Брагина Е.Ю., Фрейдин М.Б.' is a valid 2-initial byline."""
        title = _title("Genetics article title", y0=30.0)
        candidates = [
            title,
            _candidate("Брагина Е.Ю., Фрейдин М.Б.", y0=45.0),
        ]
        result = _pick_ru_authors(candidates, title)
        assert result is not None
        assert result["text"] == "Брагина Е.Ю., Фрейдин М.Б."


# ---------------------------------------------------------------------------
# TestPickRuAuthors — single-initial byline (foreign authors)
# ---------------------------------------------------------------------------
class TestPickRuAuthorsSingleInitial:
    """Single-initial authors (no patronymic) must be detected correctly."""

    def test_detects_cyrillic_single_initial(self):
        """Regression: Mh_2026-03 p67 — 'Гелприн М.' was not detected, article got _Editorial."""
        title = _title("Свеча горела", y0=90.0)
        candidates = [
            title,
            _candidate("Гелприн М.", y0=105.0),
        ]
        result = _pick_ru_authors(candidates, title)
        assert result is not None
        assert result["text"] == "Гелприн М."

    def test_detects_latin_single_initial(self):
        title = _title("The candle burned", y0=90.0)
        candidates = [
            title,
            _candidate("Gelprin M.", y0=105.0),
        ]
        result = _pick_ru_authors(candidates, title)
        assert result is not None
        assert result["text"] == "Gelprin M."

    def test_single_initial_not_confused_with_structural_label(self):
        """'Таблица А.' must not be accepted as a single-initial byline."""
        title = _title("Article title", y0=30.0)
        candidates = [
            title,
            _candidate("Таблица А.", y0=40.0),        # structural label — reject
            _candidate("Гелприн М.", y0=55.0),         # real single-initial byline
        ]
        result = _pick_ru_authors(candidates, title)
        assert result is not None
        assert result["text"] == "Гелприн М."

    def test_single_initial_preferred_over_nothing(self):
        """When only single-initial byline present, it is returned."""
        title = _title("Creative work", y0=30.0)
        candidates = [
            title,
            _candidate("Иванов А.", y0=40.0),
        ]
        result = _pick_ru_authors(candidates, title)
        assert result is not None
        assert result["text"] == "Иванов А."


# ---------------------------------------------------------------------------
# TestPickRuAuthors — regression: previously valid cases unchanged
# ---------------------------------------------------------------------------
class TestPickRuAuthorsRegression:
    """Previously accepted valid cases must still produce correct results."""

    @pytest.mark.parametrize("byline", [
        "Плоткин Ф.Б.",
        "Василькова ж.Г.",
        "Безчасный К.В.",
        "Макарова и.а.",
        "Брагина Е.Ю., Фрейдин М.Б.",
        "Plotkin F.B.",
        "Bezchasnyi K.V.",
    ])
    def test_accepts_known_valid_bylines(self, byline):
        title = _title("Article title", y0=30.0)
        candidates = [title, _candidate(byline, y0=45.0)]
        result = _pick_ru_authors(candidates, title)
        assert result is not None
        assert result["text"] == byline

    def test_title_itself_never_returned(self):
        title = _title("Название статьи В.А.", y0=30.0)
        candidates = [
            title,
            _candidate("Плоткин Ф.Б.", y0=45.0),
        ]
        result = _pick_ru_authors(candidates, title)
        assert result is not None
        assert result["text"] == "Плоткин Ф.Б."

    def test_candidate_before_title_not_returned(self):
        """Candidates with y0 < title y0 are outside the window and ignored."""
        title = _title("Title", y0=50.0)
        candidates = [
            _candidate("Плоткин Ф.Б.", y0=30.0),   # before title — ignored
            title,
        ]
        result = _pick_ru_authors(candidates, title)
        assert result is None


# ---------------------------------------------------------------------------
# TestPickEnAuthors — same gates apply to EN path
# ---------------------------------------------------------------------------
class TestPickEnAuthorsGating:
    def test_skips_running_header_finds_en_byline(self):
        title = _title("Some article in English", y0=30.0)
        candidates = [
            title,
            _candidate("Vol. 21, No. 3", y0=38.0),
            _candidate("Plotkin F.B.", y0=55.0),
        ]
        result = _pick_en_authors(candidates, title)
        assert result is not None
        assert result["text"] == "Plotkin F.B."

    def test_rejects_body_fragment(self):
        title = _title("Article title", y0=30.0)
        candidates = [
            title,
            _candidate("and other changes in the human body, stress etc.", y0=40.0),
            _candidate("Efremov A.G.", y0=55.0),
        ]
        result = _pick_en_authors(candidates, title)
        assert result is not None
        assert result["text"] == "Efremov A.G."

    def test_detects_single_initial_en(self):
        title = _title("The candle burned", y0=90.0)
        candidates = [
            title,
            _candidate("Gelprin M.", y0=105.0),
        ]
        result = _pick_en_authors(candidates, title)
        assert result is not None
        assert result["text"] == "Gelprin M."
