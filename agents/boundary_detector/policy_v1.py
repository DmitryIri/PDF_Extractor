# PDF Extractor — BoundaryDetector — ArticleStartPolicy v1.0 (Policy Table)
# Source of truth: docs/policies/article_start_policy_v_1_0.md
#
# IMPORTANT:
# - This file encodes ONLY what is explicitly defined in ArticleStartPolicy v1.0.
# - Any change MUST be done by releasing a new policy version (v1.1+).

from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Tuple


@dataclass(frozen=True)
class ArticleStartPolicyV1:
    doi_prefix: str
    doi_article_regex: re.Pattern
    ru_title_top_region: str
    required_ru_blocks: Tuple[str, ...]
    required_ru_blocks_window_pages: int
    optional_ru_blocks: Tuple[str, ...]
    optional_en_blocks: Tuple[str, ...]
    anti_signals: Tuple[str, ...]


ARTICLE_START_POLICY_V1 = ArticleStartPolicyV1(
    doi_prefix="10.25557/",
    doi_article_regex=re.compile(
        r"^10\.25557/" 
        r"(?P<journal_id>[0-9]{4}-[0-9]{4})\." 
        r"(?P<year>[0-9]{4})\." 
        r"(?P<issue>[0-9]+)\." 
        r"(?P<start_page>[0-9]+)-(?P<end_page>[0-9]+)$"
    ),
    ru_title_top_region="top_40_percent",
    required_ru_blocks=("ru_title","ru_authors","ru_affiliations","ru_address","ru_abstract"),
    required_ru_blocks_window_pages=2,
    optional_ru_blocks=("ru_keywords","ru_for_citation","ru_corresponding_author","ru_funding","ru_conflict_of_interest","ru_received_accepted"),
    optional_en_blocks=("en_title","en_authors","en_affiliations","en_abstract","en_keywords","en_for_citation","en_corresponding_author","en_funding","en_conflict_of_interest","en_received_accepted"),
    anti_signals=("doi_in_bottom_or_references_dense_list","missing_ru_abstract","missing_ru_title_max_font","doi_without_page_range","doi_repeats_on_each_odd_page_header"),
)
