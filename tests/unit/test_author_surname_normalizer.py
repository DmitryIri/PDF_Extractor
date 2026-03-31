"""Unit tests — author surname normalizer + GOST rule 3 + STEP C scan.

sys.path setup at module level: acceptable for test code only (per project convention).
"""

import os
import sys

import pytest

# ---------------------------------------------------------------------------
# sys.path — test harness only
# ---------------------------------------------------------------------------
_REPO_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
sys.path.insert(0, _REPO_ROOT)
sys.path.insert(0, os.path.join(_REPO_ROOT, "agents", "metadata_verifier"))

from shared.author_surname_normalizer import (  # noqa: E402
    is_running_header,
    is_valid_surname,
    is_toc_by_anchors,
    looks_like_author_byline,
    looks_like_single_initial_byline,
    looks_like_single_initial_byline_at_start,
    extract_single_initial_byline_prefix,
)
from verifier import (  # noqa: E402
    _transliterate_ru_to_en,
    _extract_surname_from_text_blocks,
)


# ---------------------------------------------------------------------------
# TestIsRunningHeader
# ---------------------------------------------------------------------------
class TestIsRunningHeader:
    @pytest.mark.parametrize("text", [
        "Vol. 21, No. 1",
        "Vol 21",
        "Volume 21",
        "2026; Vol. 21, No. 1",
        "Том 21, № 1",
        "2026; Том 21, № 1",
        "vol. 3, no. 2",           # case-insensitive
    ])
    def test_rejects_headers(self, text):
        assert is_running_header(text) is True

    @pytest.mark.parametrize("text", [
        "Plotkin F.B.",
        "Плоткин Ф.Б.",
        "",
        "Roschina",
        "Table A.",
    ])
    def test_accepts_non_headers(self, text):
        assert is_running_header(text) is False


# ---------------------------------------------------------------------------
# TestIsValidSurname
# ---------------------------------------------------------------------------
class TestIsValidSurname:
    # -- HARD stopwords: rejected in ALL contexts --
    @pytest.mark.parametrize("word", ["Vol", "Tom", "Contents", "Editorial", "Digest"])
    def test_rejects_hard_stopwords_global(self, word):
        assert is_valid_surname(word) is False

    @pytest.mark.parametrize("word", ["Vol", "Tom", "Contents", "Editorial", "Digest"])
    def test_rejects_hard_stopwords_step_c(self, word):
        assert is_valid_surname(word, step_c=True) is False

    # -- SOFT stopwords: rejected ONLY in step_c context --
    @pytest.mark.parametrize("word", [
        "Table", "Fig", "Figure", "Note", "Ref", "Refs",
        "Abstract", "Introduction", "Review", "Source", "Section", "Appendix",
        "Methods", "Results", "Effects",
    ])
    def test_rejects_soft_stopwords_in_step_c(self, word):
        assert is_valid_surname(word, step_c=True) is False

    @pytest.mark.parametrize("word", ["Table", "Fig", "Note"])
    def test_accepts_soft_stopwords_in_global(self, word):
        # SOFT words pass in global context — intentional per HARD/SOFT contract
        assert is_valid_surname(word, step_c=False) is True

    # -- structural rejects --
    def test_rejects_single_char(self):
        assert is_valid_surname("A") is False

    def test_rejects_empty(self):
        assert is_valid_surname("") is False

    def test_rejects_two_char_allcaps(self):
        assert is_valid_surname("AB") is False

    def test_rejects_digit_in_word(self):
        assert is_valid_surname("Tp1") is False

    def test_rejects_lowercase_vol(self):
        # "vol" capitalises to "Vol" → HARD stopword hit
        assert is_valid_surname("vol") is False

    # -- target surnames: must all pass --
    @pytest.mark.parametrize("word", [
        "Roschina", "Efremov", "Bezchasnyi", "Zhukova", "Plotkin",
        "Makarova", "Kazakovtsev", "Orlov",
    ])
    def test_accepts_target_surnames(self, word):
        assert is_valid_surname(word) is True


# ---------------------------------------------------------------------------
# TestIsTocByAnchors
# ---------------------------------------------------------------------------
class TestIsTocByAnchors:
    _ANCHORS = [
        {"type": "contents_marker", "page": 2},
        {"type": "ru_title", "page": 3},
        {"type": "contents_marker", "page": 5},   # second TOC marker (edge case)
    ]

    def test_true_when_marker_inside_range(self):
        # contents_marker on page 2, article spans 1-2
        assert is_toc_by_anchors(1, 2, self._ANCHORS) is True

    def test_false_when_marker_outside_range(self):
        # contents_marker on pages 2 and 5; article spans 3-4 (neither 2 nor 5)
        assert is_toc_by_anchors(3, 4, self._ANCHORS) is False

    def test_true_second_marker_in_range(self):
        # contents_marker on page 5, article spans 3-6
        assert is_toc_by_anchors(3, 6, self._ANCHORS) is True

    def test_false_no_markers(self):
        assert is_toc_by_anchors(1, 10, [{"type": "ru_title", "page": 1}]) is False

    def test_false_empty_anchors(self):
        assert is_toc_by_anchors(1, 5, []) is False


# ---------------------------------------------------------------------------
# TestLooksLikeAuthorByline  (2-initial regex)
# ---------------------------------------------------------------------------
class TestLooksLikeAuthorByline:
    @pytest.mark.parametrize("text", [
        "Plotkin F.B.",
        "Zhukova d.i.",
        "roschina o.V.",
        "Безчасный К.В.",
        "Макарова и.а.",
        "Плоткин Ф.Б.",
        "Kazakovtsev B.a.",
        "жукова д.и.",
    ])
    def test_accepts_two_initial_bylines(self, text):
        assert looks_like_author_byline(text) is True

    @pytest.mark.parametrize("text", [
        "Оригинальное исследование",   # no period after initial
        "Keywords: temperature",       # colon not in separator set
        "Introduction",                # single word
        "Table A.",                    # single initial -> REJECTED structurally
        "Note C.",                     # single initial -> REJECTED
        "Vol. 21, No. 1",             # period not a separator
        "Том 21, № 1",                # digit not a letter
        "Fig. 1.",                     # Fig + period (not separator)
        "Section 3.",                  # digit not a letter
        "",
    ])
    def test_rejects_non_bylines(self, text):
        assert looks_like_author_byline(text) is False


# ---------------------------------------------------------------------------
# TestGostRule3  (ый → yi at word end)
# ---------------------------------------------------------------------------
class TestGostRule3:
    def test_bezchasnyi(self):
        assert _transliterate_ru_to_en("Безчасный") == "Bezchasnyi"

    def test_zaytsev_unaffected(self):
        # й after а (not ы) → standard 'y'
        assert _transliterate_ru_to_en("Зайцев") == "Zaytsev"

    def test_gorovoy_unaffected(self):
        # й after о (not ы) → standard 'y'
        assert _transliterate_ru_to_en("Горовой") == "Gorovoy"

    def test_mid_word_yy_unaffected(self):
        # й after ы but NOT at word end (followed by Cyrillic) → standard 'y'
        assert _transliterate_ru_to_en("Выйти") == "Vyyti"

    def test_existing_rule_ie_still_works(self):
        assert _transliterate_ru_to_en("Муртазалиева") == "Murtazaliyeva"

    def test_existing_rule_niu_still_works(self):
        assert _transliterate_ru_to_en("Гуменюк") == "Gumeniuk"


# ---------------------------------------------------------------------------
# TestStepCScan  (N=6 bounded text_block scan)
# ---------------------------------------------------------------------------
class TestStepCScan:
    """Scenarios verified against Plan-03 §8.1 TestStepCScan."""

    # -- Scenario 1: section label before real byline → label skipped --
    def test_skips_non_byline_picks_first_valid(self):
        anchors = [
            {"type": "text_block", "page": 26, "text": "Оригинальное исследование"},
            {"type": "text_block", "page": 26, "text": "Plotkin F.B."},
            {"type": "text_block", "page": 26, "text": "X" * 50},   # long text, no byline pattern
        ]
        result = _extract_surname_from_text_blocks(26, anchors)
        assert result is not None
        assert result["first_author_surname"] == "Plotkin"
        assert result["first_author_surname_source"] == "text_block"

    # -- Scenario 2: HARD stopword in text_block with 2 initials --
    # "Vol F.B." passes the 2-initial regex but "Vol" is a HARD stopword → rejected.
    def test_hard_stopword_blocks_before_real_byline(self):
        anchors = [
            {"type": "text_block", "page": 26, "text": "Vol F.B."},
            {"type": "text_block", "page": 26, "text": "Plotkin F.B."},
        ]
        result = _extract_surname_from_text_blocks(26, anchors)
        assert result is not None
        assert result["first_author_surname"] == "Plotkin"

    # -- Scenario 3: RU / EN mixed → RU candidate preferred (GOST canonical) --
    def test_ru_candidate_preferred_over_en(self):
        anchors = [
            {"type": "text_block", "page": 26, "text": "Introduction section"},  # fails byline
            {"type": "text_block", "page": 26, "text": "Плоткин Ф.Б."},          # RU byline
            {"type": "text_block", "page": 26, "text": "Plotkin F.B."},           # EN byline
        ]
        result = _extract_surname_from_text_blocks(26, anchors)
        assert result is not None
        assert result["first_author_surname"] == "Plotkin"
        assert result["first_author_surname_source"] == "text_block_translit"

    # -- Scenario 4: N=6 exhaustion → returns None --
    # N=6 counts only byline-pattern candidates (not all text_blocks).
    # Use 6 stopword-blocked bylines to exhaust the limit; the real target
    # sits at candidate index 6 (outside N=6).  Non-byline noise before them
    # is transparent to the counter.
    def test_n6_boundary_enforced(self):
        anchors = [
            # noise blocks — transparent to N (no byline pattern)
            {"type": "text_block", "page": 26, "text": "Section 1"},
            {"type": "text_block", "page": 26, "text": "26"},              # page number
            # 6 byline-pattern blocks rejected by HARD/SOFT stopwords → exhaust N=6
            {"type": "text_block", "page": 26, "text": "Vol A.B."},        # HARD
            {"type": "text_block", "page": 26, "text": "Tom A.B."},        # HARD
            {"type": "text_block", "page": 26, "text": "Table X.Y."},      # SOFT
            {"type": "text_block", "page": 26, "text": "Note A.B."},       # SOFT
            {"type": "text_block", "page": 26, "text": "Fig A.B."},        # SOFT
            {"type": "text_block", "page": 26, "text": "Ref A.B."},        # SOFT
            # candidate index 6 — outside N=6 window:
            {"type": "text_block", "page": 26, "text": "Plotkin F.B."},
        ]
        result = _extract_surname_from_text_blocks(26, anchors)
        assert result is None

    # -- Scenario 5: only EN candidate found (no RU) → EN returned --
    def test_en_only_candidate(self):
        anchors = [
            {"type": "text_block", "page": 10, "text": "Efremov A.G."},
        ]
        result = _extract_surname_from_text_blocks(10, anchors)
        assert result is not None
        assert result["first_author_surname"] == "Efremov"
        assert result["first_author_surname_source"] == "text_block"

    # -- Scenario 6: running header in text_block → skipped --
    def test_running_header_skipped(self):
        anchors = [
            {"type": "text_block", "page": 37, "text": "Vol. 21, No. 1"},   # header
            {"type": "text_block", "page": 37, "text": "Безчасный К.В."},   # real byline
        ]
        result = _extract_surname_from_text_blocks(37, anchors)
        assert result is not None
        assert result["first_author_surname"] == "Bezchasnyi"
        assert result["first_author_surname_source"] == "text_block_translit"


# ---------------------------------------------------------------------------
# TestLooksLikeSingleInitialByline  (single-initial byline: "Surname I.")
# ---------------------------------------------------------------------------
class TestLooksLikeSingleInitialByline:
    # -- accept: foreign authors without patronymic --
    @pytest.mark.parametrize("text", [
        "Гелприн М.",          # Cyrillic, case from Mh_2026-03
        "Gelprin M.",          # Latin equivalent
        "Иванов А.",           # standard single-initial Cyrillic
        "Smith J.",            # standard single-initial Latin
        "Гелприн М. ",         # trailing whitespace allowed
    ])
    def test_accepts_single_initial_bylines(self, text):
        assert looks_like_single_initial_byline(text) is True

    # -- reject: 2-initial bylines (handled by looks_like_author_byline) --
    @pytest.mark.parametrize("text", [
        "Плоткин Ф.Б.",        # 2-initial RU — NOT single-initial
        "Plotkin F.B.",        # 2-initial EN
        "Василькова ж.Г.",     # 2-initial RU with lowercase first initial
    ])
    def test_rejects_two_initial_bylines(self, text):
        # These are valid author bylines but handled by looks_like_author_byline, not here
        assert looks_like_single_initial_byline(text) is False

    # -- reject: structural labels --
    @pytest.mark.parametrize("text", [
        "Таблица А.",
        "Рисунок В.",
        "Рис А.",
        "Приложение Б.",
        "Table A.",
        "Figure B.",
        "Fig C.",
        "Appendix D.",
    ])
    def test_rejects_structural_labels(self, text):
        assert looks_like_single_initial_byline(text) is False

    # -- reject: body-text fragments with initials in the middle --
    @pytest.mark.parametrize("text", [
        "Анализируя труды В.Д.",          # multi-word before initial
        "ским и другим изменениям В.Д.",  # fragment from body
        "Том 21, № 3",                    # running header
        "Introduction A.",                # non-byline structural
        "",
        "А.",                             # only initial, no surname
        "М.",                             # only initial
    ])
    def test_rejects_non_bylines(self, text):
        assert looks_like_single_initial_byline(text) is False


# ---------------------------------------------------------------------------
# TestLooksLikeSingleInitialBylineAtStart
# ---------------------------------------------------------------------------

class TestLooksLikeSingleInitialBylineAtStart:
    """Prefix-only variant: byline merged with following body text."""

    # -- accept: byline at start of merged text --
    @pytest.mark.parametrize("text", [
        "Гелприн М. Рассказ Майка Гелприна «Свеча горела» разворачивается",
        "Gelprin M. Mike Gelprin's short story is set in a future",
        "Иванов А. Аннотация: исследование показало что",
        "Smith J. The study examined outcomes in patients",
    ])
    def test_accepts_byline_at_start(self, text):
        assert looks_like_single_initial_byline_at_start(text) is True

    # -- reject: full-string single-initial (handled by looks_like_single_initial_byline) --
    @pytest.mark.parametrize("text", [
        "Гелприн М.",      # full string — use looks_like_single_initial_byline instead
        "Gelprin M.",
    ])
    def test_rejects_full_string_bylines(self, text):
        # Requires trailing whitespace after period to match; full strings have no trailing space
        assert looks_like_single_initial_byline_at_start(text) is False

    # -- reject: structural labels at start --
    @pytest.mark.parametrize("text", [
        "Таблица А. Данные исследования показали",
        "Figure B. Comparison of results",
    ])
    def test_rejects_structural_labels_at_start(self, text):
        assert looks_like_single_initial_byline_at_start(text) is False

    # -- reject: body text not starting with byline --
    @pytest.mark.parametrize("text", [
        "Рассказ Майка Гелприна разворачивается в мире будущего",
        "Introduction to the study and its objectives",
        "",
        "М. Гелприн написал рассказ",  # initial before surname, not byline format
    ])
    def test_rejects_non_byline_start(self, text):
        assert looks_like_single_initial_byline_at_start(text) is False


# ---------------------------------------------------------------------------
# TestExtractSingleInitialBylinePrefix
# ---------------------------------------------------------------------------

class TestExtractSingleInitialBylinePrefix:
    """Prefix extraction — returns just the byline token from merged text."""

    @pytest.mark.parametrize("text, expected", [
        ("Гелприн М. Рассказ Майка Гелприна разворачивается", "Гелприн М."),
        ("Gelprin M. Mike Gelprin's story is set in a future", "Gelprin M."),
        ("Иванов А. Аннотация: исследование показало", "Иванов А."),
    ])
    def test_extracts_prefix(self, text, expected):
        assert extract_single_initial_byline_prefix(text) == expected

    @pytest.mark.parametrize("text", [
        "Гелприн М.",        # full-string byline (no trailing space+text) — prefix RE needs \s
        "Gelprin M.",
        "Рассказ Майка Гелприна разворачивается",
        "Таблица А. Данные показали",  # structural label
        "",
    ])
    def test_returns_none(self, text):
        assert extract_single_initial_byline_prefix(text) is None
