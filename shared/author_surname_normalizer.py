"""Pure functions for author surname normalization.

No I/O, no agent imports.  Used by MetadataVerifier (STEP A-C).

Stopword contract:
    HARD  — applied globally (STEP A, B, C).  Running-header and service-label words
            that can appear in ru_authors / en_authors anchor text.
    SOFT  — applied only in STEP C (text_block scan).  Structural labels that appear
            only in text_block content, never in author anchors.
    Callers pass step_c=True when invoking from STEP C context.
"""

import re as _re
from typing import Optional as _Optional

# ---------------------------------------------------------------------------
# Running-header detection
# ---------------------------------------------------------------------------
# Matches journal volume/issue headers in EN and RU.
# EN: "Vol. 21, No. 1", "Vol 21", "Volume 21", "2026; Vol. 21, No. 1"
# RU: "Том 21, № 1", "2026; Том 21, № 1"
_HEADER_RE = _re.compile(
    r'(?:^|;\s*)'                        # start of string or after semicolon
    r'(?:Vol(?:ume)?\.?\s+\d|Том\s+\d)', # Vol/Volume/Том + digit
    _re.IGNORECASE
)


def is_running_header(text: str) -> bool:
    """Return True if *text* matches a running-header pattern (Vol / Том)."""
    if not text:
        return False
    return bool(_HEADER_RE.search(text.strip()))


# ---------------------------------------------------------------------------
# Stopwords
# ---------------------------------------------------------------------------
STOPWORDS_HARD = {
    # Running-header words (observed in ru_authors / en_authors anchors)
    "Vol", "Tom",
    # Service-material labels
    "Contents", "Editorial", "Digest",
}

STOPWORDS_SOFT = {
    # Structural labels that produce Word-Initial-Period patterns in text_blocks
    "Table", "Fig", "Figure", "Note", "Ref", "Refs",
    "Abstract", "Introduction", "Review", "Source", "Section", "Appendix",
    "Methods", "Results", "Effects",
}


def is_valid_surname(surname: str, step_c: bool = False) -> bool:
    """Validate candidate surname against stopwords and structural rules.

    step_c=True enables SOFT stopwords (use only when called from STEP C).
    """
    if not surname or len(surname) < 2:
        return False

    # Capitalise first char for stopword lookup ("vol" -> "Vol")
    word = surname[0].upper() + surname[1:]

    if word in STOPWORDS_HARD:
        return False
    if step_c and word in STOPWORDS_SOFT:
        return False

    # --- structural rejects (mirrors _validate_surname_en logic) -----------
    if _re.search(r'\d', surname):           # digits -> gene symbol / rsID
        return False
    if _re.match(r'^rs\d+', surname, _re.IGNORECASE):
        return False
    if surname.isupper() and len(surname) <= 8:   # short ALL-CAPS -> gene
        return False
    if '(' in surname or ')' in surname:     # biological notation
        return False

    # Must start uppercase + lowercase after capitalisation
    if not _re.match(r'^[A-Z][a-z]', word):
        return False

    return True


# ---------------------------------------------------------------------------
# TOC detection — anchor-based, no page-number hardcodes
# ---------------------------------------------------------------------------
def is_toc_by_anchors(from_page: int, to_page: int, anchors: list) -> bool:
    """Return True if any *contents_marker* anchor falls within [from_page, to_page].

    Universally correct: works for TOC of any length and any journal,
    because it relies only on MetadataExtractor-emitted anchor data.
    """
    for anchor in anchors:
        if anchor.get("type") == "contents_marker":
            p = anchor.get("page")
            if p is not None and from_page <= p <= to_page:
                return True
    return False


# ---------------------------------------------------------------------------
# Author-byline detection — 2-initial requirement
# ---------------------------------------------------------------------------
# Matches "Surname I.I." in Latin or Cyrillic.
# Requiring two initials structurally rejects single-initial labels
# ("Table A.", "Note C.") without relying on stopwords.
# RU bilingual journals use 2-initial format (FirstName.Patronymic.) universally.
_BYLINE_RE = _re.compile(
    r'^[A-Za-zА-Яа-яЁё]+'        # Surname word
    r'[\s,]+'                     # Separator (space / comma)
    r'[A-Za-zА-ЯЁёа-яё]\.'      # First initial + period
    r'\s*'                        # Optional space between initials
    r'[A-Za-zА-ЯЁёа-яё]\.',     # Second initial + period
    _re.UNICODE
)


def looks_like_author_byline(text: str) -> bool:
    """Return True if *text* matches a 2-initial author byline pattern."""
    if not text:
        return False
    return bool(_BYLINE_RE.match(text.strip()))


# ---------------------------------------------------------------------------
# Single-initial byline — foreign authors without patronymic
# ---------------------------------------------------------------------------
# Matches "Surname I." where the string consists entirely of one word + one
# initial (anchored at both ends).  Requires full-string match to prevent
# body-text fragments like "Анализируя труды В.Д." from matching.
_SINGLE_INITIAL_BYLINE_RE = _re.compile(
    r'^[A-Za-zА-Яа-яЁё]+'   # Surname (exactly one word)
    r'[\s,]+'                 # Separator (space / comma)
    r'[A-Za-zА-ЯЁёа-яё]\.'  # ONE initial + period
    r'\s*$',                  # End of string (optional trailing whitespace)
    _re.UNICODE
)

# Structural labels that form "Word X." patterns but are NOT author bylines.
# Guard against false positives in single-initial detection.
_SINGLE_INITIAL_STRUCTURAL_LABELS = frozenset({
    "Таблица", "Рисунок", "Рис", "Схема", "Приложение", "Пример",
    "Table", "Figure", "Fig", "Appendix",
})


def looks_like_single_initial_byline(text: str) -> bool:
    """Return True if *text* is a single-initial author byline: 'Surname I.'

    Handles foreign authors without patronymic (e.g. 'Гелприн М.', 'Gelprin M.').
    Rejects structural labels ('Таблица А.', 'Рисунок В.', 'Introduction A.').
    Does NOT match multi-word body-text fragments — anchored at both ends.
    """
    if not text:
        return False
    t = text.strip()
    if not _SINGLE_INITIAL_BYLINE_RE.match(t):
        return False
    first_word = t.split()[0].rstrip('.,;:')
    # Capitalise for stopword lookup (same convention as is_valid_surname)
    first_word_cap = first_word[0].upper() + first_word[1:] if first_word else ""
    if first_word in _SINGLE_INITIAL_STRUCTURAL_LABELS:
        return False
    if first_word_cap in STOPWORDS_HARD or first_word_cap in STOPWORDS_SOFT:
        return False
    return True


# Prefix-only variant of _SINGLE_INITIAL_BYLINE_RE: matches 'Surname I.' at the
# START of a longer string (e.g. after merge with body text during grouping).
# The trailing \s ensures the initial period ends the byline token, not mid-word.
_SINGLE_INITIAL_BYLINE_START_RE = _re.compile(
    r'^([A-Za-zА-Яа-яЁё]+'   # Surname (one word)
    r'[\s,]+'                  # separator
    r'[A-Za-zА-ЯЁёа-яё]\.)'  # ONE initial + period
    r'\s',                     # must be followed by whitespace (not end-of-string)
    _re.UNICODE
)


def looks_like_single_initial_byline_at_start(text: str) -> bool:
    """Return True if *text* STARTS WITH a single-initial author byline.

    Used when a byline was merged with following body text during grouping
    (e.g. 'Гелприн М. Рассказ Майка...' → prefix 'Гелприн М.' is a byline).
    Applies the same structural-label and stopword guards as
    looks_like_single_initial_byline().
    """
    if not text:
        return False
    t = text.strip()
    m = _SINGLE_INITIAL_BYLINE_START_RE.match(t)
    if not m:
        return False
    # Validate the extracted prefix through the full single-initial check
    return looks_like_single_initial_byline(m.group(1))


def extract_single_initial_byline_prefix(text: str) -> _Optional[str]:
    """Extract the single-initial byline prefix from text that starts with one.

    Returns the prefix (e.g. 'Гелприн М.') when the text is a merged block
    where a byline was joined with following body text during grouping.
    Returns None if the text does not start with a valid single-initial byline.

    Used by MetadataExtractor to emit only the byline portion as ru_authors
    anchor text — avoids emitting the full merged body block (which would
    trigger _is_editorial_greeting's > 200 char check in BoundaryDetector).
    """
    if not text:
        return None
    t = text.strip()
    m = _SINGLE_INITIAL_BYLINE_START_RE.match(t)
    if not m:
        return None
    prefix = m.group(1)
    if looks_like_single_initial_byline(prefix):
        return prefix
    return None
