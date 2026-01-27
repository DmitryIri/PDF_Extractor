# PDF Extractor — BoundaryDetector — ArticleStartDetection Policy v_1_0 (Typography-based)
# Source of truth: docs/policies/article_start_detection_policy_v_1_0.md
#
# IMPORTANT:
# - This file encodes ONLY what is explicitly defined in ArticleStartDetection Policy v_1_0.
# - Any change MUST be done by releasing a new policy version (v_1_1+).

from __future__ import annotations

from dataclasses import dataclass
from typing import Tuple


@dataclass(frozen=True)
class ArticleStartDetectionPolicyV1:
    """Typography-based article start detection policy."""

    # PRIMARY SIGNAL: Typography marker
    primary_font_name: str
    primary_font_size: float
    primary_font_size_tolerance: float
    primary_min_text_length: int

    # FILTER: Language-based duplicate detection
    duplicate_filter_enabled: bool

    # BLACKLIST: Known false positives (case-insensitive matching)
    blacklist: Tuple[str, ...]


ARTICLE_START_DETECTION_POLICY_V1 = ArticleStartDetectionPolicyV1(
    # PRIMARY SIGNAL (from golden test)
    primary_font_name="MyriadPro-BoldIt",
    primary_font_size=12.0,
    primary_font_size_tolerance=0.5,
    primary_min_text_length=10,

    # DUPLICATE FILTER
    duplicate_filter_enabled=True,

    # BLACKLIST (from golden test)
    blacklist=(
        "2025. том 24. номер 12",
        "оригинальное исследование",
        "краткое сообщение",
    ),
)
