# Project History Log

**Проект:** PDF Extractor  
**Статус:** Canonical  
**Назначение:** Кумулятивная история ключевых событий и вех проекта.

---

## 2026-01-22
- **GitHub remote configured (origin), sync deferred until Phase 2 completion**: GitHub repo `DmitryIri/PDF_Extractor` will be stitched/merged after Phase 2; current SoT remains `/opt/projects/pdf-extractor`.
- **Audit exports infrastructure established** (commit 34344ad):
  - Создана `.claude/rules/audit_exports.md` — canonical policy для Claude Code /export artifacts
  - Создан `.claude/skills/archive-exports/SKILL.md` — reusable skill для архивации экспортов
  - Создан `.claude/settings.json` — project-level permissions (git-tracked)
  - Определены канонические пути: `_audit/claude_code/exports/`, `_audit/claude_code/reports/`
- **TechSpec v_2_5 committed** (commit 5c4abd3):
  - Добавлена спецификация stdin envelope + stdout/stderr contract
  - Формализована typography-based detection (PRIMARY SIGNAL)
  - Документирована rich article_starts schema
- **Documentation alignment completed** (commit 71315ff):
  - Plan v_2_3 обновлён: все ссылки на TechSpec v_2_4 заменены на v_2_5
  - BoundaryDetector v_1_1 создан как minimal patch от v_1_0 (синхронизация с TechSpec v_2_5)
- **Verification evidence generated** (не закоммитено, в `_audit/claude_code/reports/`):
  - Verification artifacts для BoundaryDetector v_1_1 claims (vs TechSpec + code)
  - TechSpec v_2_4 → v_2_5 full patch + diffstat
  - SHA256 manifests для аудита
- Project Summary v_2_8 создан
- **Status**: Все коммиты local-only (branch: feature/phase-2-core-autonomous), push не выполнялся

- **Session closure logs synced into repo** (commit c799feb):
  - Добавлены отсутствующие `session_closure_log_*.md` в `docs/state/` (итого 16 файлов)
- **Plan v_2_4 created to resolve doc-mismatch** (commits 3a43ea9, b7da1f7):
  - Acceptance: `confidence == 1.0` (binary match) + rich `article_starts` objects
  - Исправлены заголовок и canonical marker внутри `pdf_extractor_plan_v_2_4.md`
- **Project Summary pointers updated to Plan v_2_4** (commit c2ee87c):
  - `project_summary_v_2_8.md` теперь указывает Canonical Plan = v_2_4

## 2026-01-23
- **Phase 2.5 BoundaryDetector completed** (commit cf75aa9):
  - Golden test artifacts committed: `mg_2025_12_anchors.json` (18,184 anchors), `mg_2025_12_boundaries.json` (28 article_starts + boundary_ranges), `mg_2025_12_article_starts.json` (canonical reference)
  - Verifier script added: `scripts/verify_boundary_detector_golden.py` — validates article_starts against golden reference, checks confidence == 1.0, verifies boundary_ranges invariants
  - Determinism proven: 2 runs → identical output (10,507 bytes)
- **MetadataExtractor stdout/stderr contract fix** (commit cbc625c):
  - Changed JSON emission to use `os.write(1, json_bytes)` for explicit fd1 output per TechSpec v_2_5
  - Fixes contract violation where JSON was emitted to stderr
  - Tested: anchors.json 5,049,995 bytes (18,184 anchors, 156 pages), stderr 0 bytes, exit_code 0
- **.gitignore exception for golden_tests JSON** (commit bd169c6):
  - Added `!golden_tests/**/*.json` exception to allow tracking golden test artifacts
  - Prevents accidental tracking of runtime artifacts while enabling canonical references
- **docs/design hygiene completed** (commit 28d168d):
  - Archived non-canonical design artifacts (git mv, history preserved):
    - `pdf_extractor_techspec_v_2_4.md` → `docs/_archive/techspec/` (superseded by v_2_5)
    - `pdf_extractor_boundary_detector_v_1_0.md` → `docs/_archive/design/` (superseded by v_1_1)
  - Updated references: CLAUDE.md primary documentation pointer (v_2_4 → v_2_5), boundary_detector_v_1_1.md previous version link
  - Canonical KEEP list: TechSpec v_2_5, Plan v_2_4, BoundaryDetector v_1_1
- **Phase 2.6 Splitter completed (Plan v_2_4 §5.6, Шаг 2.5: lines 157-169)** (commits 3bbf4a1, 93a69ec):
  - Physical PDF splitting by boundary ranges from BoundaryDetector
  - Canonical PDF: `/srv/pdf-extractor/tmp/Mg_2025-12.pdf` (~8.3 MB; 8345036 bytes)
  - Article PDFs created: 28 (pages 5-156)
  - Determinism verified: SHA256 hashes stable across 2 independent runs
  - Verifier script: `scripts/verify_splitter_golden.py` — validates PDFs against golden boundaries
  - Golden artifact: `golden_tests/mg_2025_12_splitter_output.json` (8,765 bytes)
  - Export archived: `_audit/claude_code/exports/2026_01_23__10_15_32/2026-01-23-bootstrap-only-do-not-run-any-long-commands.txt` (SHA256: 7a8eb86a7221bab6125832fd5cd53131da82eae03ccbd79bc607fa91d25a8074)
- **Phase 2.6 MetadataVerifier completed** (commit 6d67412):
  - Manifest verification + enrichment для OutputBuilder readiness
  - Validates: required fields, page ranges, file existence, naming rules
  - Enriches: journal_code, issue_prefix, expected_filename, splitter_output metadata (sha256, bytes)
  - Deterministic output: sort_keys, stable article ordering
  - Test fixture: `tests/fixtures/metadata_verifier_input_minimal.json` (3 articles)
- **Status**: Все коммиты local-only (branch: feature/phase-2-core-autonomous), push не выполнялся

## 2026-01-26
- **Phase 2.7 OutputBuilder completed (Plan v_2_4 §5.8, Шаг 2.7)**:
  - Implemented `agents/output_builder/builder.py` (v_1_0.0)
  - Stdin/stdout envelope contract per TechSpec v_2_5
  - Atomic export: сборка в `{export_id}.tmp/` → atomic rename в `{export_id}/`
  - Export structure: `/srv/pdf-extractor/exports/{JournalCode}/{YYYY}/{IssuePrefix}/exports/{export_id}/`
    - `articles/` — Article PDFs с canonical naming: `{IssuePrefix}_{PPP-PPP}_{FirstAuthorSurname}.pdf`
    - `manifest/export_manifest.json` — Export metadata (journal, issue, articles list, timestamps)
    - `checksums.sha256` — SHA256 checksums для всех article PDFs (SHA256SUMS format)
    - `README.md` — Human-readable export documentation с verification instructions
  - Exit codes: 0=success, 10=invalid_input, 40=build_failed, 50=internal_error
  - Naming rule enforcement: 3-digit zero-padded page numbers per session_closure_log_2026_01_23_v_1_2.md §3.1
  - Deterministic export_id generation: `YYYY_MM_DD__HH_MM_SS` (UTC timestamp)
- **OutputBuilder testing**:
  - Unit tests: `tests/test_output_builder.sh` (5 тестов: 1 happy path + 4 negative)
  - Test coverage: missing fields, invalid formats, non-existent source PDFs
  - Integration test: MetadataVerifier → OutputBuilder pipeline успешен (3 статьи экспортированы)
  - Checksums validated: `sha256sum -c checksums.sha256` → all OK
- **Test fixtures**:
  - Added `tests/fixtures/output_builder_input_minimal.json` (2 articles minimal example)
- **Documentation updates**:
  - Created Project Summary v_2_9 (from v_2_8)
  - Updated project_history_log.md
  - Documented decision D4: Canonical Export Structure (FS-only, no DB/UI)
  - Documented known limitation Q1: source of `first_author_surname` (между Splitter и MetadataVerifier)
- **Активная фаза:** Phase 2.7 → Phase 2.8 (OutputValidator next)
- **Status**: Все коммиты local-only (branch: feature/phase-2-core-autonomous), push не выполнялся

## 2026-01-14
- Инициализирован `project_history_log.md` как канонический State-артефакт.
- Зафиксирован и размещён канонический `PROJECT_FILES_INDEX v_1_2`.
- Документ доведён до Claude-ready состояния (физические пути + сценарий Claude Code Bootstrap).
- Снят блокер для начала работы в Claude Code.

## 2026-02-04
- **Docs canonicalization (docs(canon) session):**
  - Archived superseded design docs: techspec v_2_5, boundary_detector v_1_1
  - Archived superseded summaries: v_2_6 through v_2_10
  - Archived working artifact: REPORT_universal_surname_selection_fix_exec.md
  - Removed pre-sync duplicate: `_archive/session_logs/session_closure_log_2026_01_12_v1_0.md` (exact copy in docs/state/)
  - canonical_artifact_registry v_1_1 → v_1_2: added §5 Policy Documents type
  - project_files_index v_1_7 → v_1_8: explicit canonical pointers, archive notes, task_specs/ registered
  - Created `_archive/legacy_aliases/2026_02_04/README.md` — full move manifest
  - Known immutable refs noted: TechSpec v_2_6 and BD v_1_2 reference filename_generation_policy_v_1_0 (historically accurate; cannot patch immutable files)
  - Session closure log naming inconsistency noted (mixed dots/underscores) — no rename (preserves git history refs)

- **Universal Surname Selection Fix complete (Plan-03):**
  - MetadataVerifier v1.2.0 → v1.3.0: STEP A→B→C surname extraction with running-header filter, 2-initial byline regex, HARD/SOFT stopwords, GOST rule 3 (ый→yi), TOC re-verification by anchors
  - New module: `shared/author_surname_normalizer.py` — pure functions (is_running_header, is_valid_surname, is_toc_by_anchors, looks_like_author_byline)
  - Unit tests: `tests/unit/test_author_surname_normalizer.py` — 88 tests, all pass
  - Policy: `docs/policies/filename_generation_policy_v_1_1.md` (MINOR bump)
  - DEVIATION from Plan-03: N=6 scan counts byline-pattern candidates only (not all text_blocks); running headers and structural noise are transparent to the limit
  - Acceptance: Mg golden regression PASS (byte-for-byte); Mh_2026-01 all 9 filenames correct; zero header-surnames
  - Commits: see feat(surname-fix) + docs commits below
  - **Phase 3 bootstrap stub created:** `docs/governance/task_specs/task_spec_phase_3_ui_db_bootstrap_v_1_0.md`

- **Housekeeping session (same date, later):**
  - /archive-exports executed: 5 export files → `_audit/claude_code/exports/2026_02_04__13_13_14/`, sha256 verified 5/5 OK, root cleaned.
  - Bugfix: archive-exports SKILL.md v_1_0 → v_1_1 — added sha256sum -c verification gate anchored at repo root (latent bug: spec had no verification step; runtime improvisation used `cd "$ARCH"` + relative path which failed).
  - .claude/* versioning confirmed (3 files already tracked); committed 4 previously-untracked skills/rules — SHA **df35880**.
  - .gitignore: added `.claude/skills/**/*.bak_*`, removed 2 stale .bak files — SHA **44e3843**.
  - settings.json: added `Bash(git show:*)`, `Bash(git check-ignore:*)` — SHA **f0804ca**.
  - settings.local.json sanitized: 93 → 43 entries (removed __NEW_LINE_ artifacts, /tmp/ paths, heredocs, dups, loop fragments, hardcoded session IDs). Untracked, backup created + deleted, tree clean.

## Material Classification Implementation & RU-Journal Filename Policy (2026-01-26)

**Session Context:** Four-phase implementation fixing filename generation for RU-journals (Mg_2025-12 issue)

**Problem Identified:**
- Forensic analysis revealed gene symbols (TPM1, LPL, rs1143634) appearing in filenames instead of author surnames
- Root cause: en_authors anchors incorrectly extracted from gene symbols in EN metadata blocks
- RU-journal policy violation: EN metadata was PRIMARY, RU metadata was FALLBACK (should be inverted)
- Contents (pages 1-4) and Editorial (page 5) misclassified as research articles
- Page 110-112: ru_title "Патогенетика..." leaked into ru_authors, causing wrong filename

**Component Versions:**
- MetadataExtractor: v1.3.0 → v1.3.1
- BoundaryDetector: v1.1.0 → v1.2.0
- MetadataVerifier: v1.1.0 → v1.2.0

**Changes:**

**1. MetadataVerifier v1.2.0 (filename_generation_policy_v_1_0 for RU-journals):**
- **Inverted priority:** ru_authors PRIMARY, en_authors FALLBACK (with validation)
- **Gene/rsID filtering:** Added _validate_surname_en() to reject:
  - rsID patterns (rs\d+)
  - Biological notation (parentheses)
  - All-caps short words (≤8 chars, likely gene symbols)
  - Strings with digits
- **Transliteration hierarchy:**
  1. Author's own transliteration (from en_authors on same page as ru_authors)
  2. GOST 7.79-2000 System B with context rules ("ие"→"iye", "ню"→"niu")
- **Evidence tracking:** Added first_author_surname_source field:
  - ru_authors_author_translit (author's own)
  - ru_authors_translit (GOST mechanical)
  - en_authors_validated (EN-only fallback)

**2. BoundaryDetector v1.2.0 (Contents/Editorial detection):**
- **Front-matter detection:** Added _detect_contents_on_first_pages() for special-case Contents detection (max_page=4) using contents_marker anchor
- **Editorial filtering:** Added _is_editorial_greeting() to filter editorial greetings/signatures:
  - Short greetings (academic title + short phrase)
  - Long signatures (>200 chars with academic titles)
- **Editorial isolation:** Changed _classify_material_kind() to use window=0 (same page only) for editorial detection to prevent capturing next page's authors

**3. MetadataExtractor v1.3.1 (ru_title/ru_authors separation):**
- **Text-based exclusion:** Modified _pick_ru_authors() and _pick_en_authors() to skip candidates with same text as ru_title/en_title
- **Semantic heuristic:** Added _is_likely_title_not_authors() to detect article titles vs author lists:
  - Title indicators: ≥3 lowercase words, no initials pattern
  - Author indicators: initials present + ≥2 commas
- **Fail-fast:** No error suppression in surname extraction

**Material Kind Taxonomy:**
- contents: Multi-page table of contents
- editorial: Editorial/foreword without extractable authors
- research: Research articles with extractable first author
- digest: Digest/summary materials (journal-specific)

**Naming Rules:**
- contents → {IssuePrefix}_{PPP-PPP}_Contents.pdf
- editorial → {IssuePrefix}_{PPP-PPP}_Editorial.pdf
- digest → {IssuePrefix}_{PPP-PPP}_Digest.pdf
- research → {IssuePrefix}_{PPP-PPP}_{Surname}.pdf

**Verification:**
- Golden test: tests/test_material_classification_golden.sh
- Result: ✅ EXACT MATCH on all 29 articles for Mg_2025-12
- Reference: docs/state/reference_inputs_manifest_mg_2025_12_v_1_0.json
- Key fixes verified:
  - Mg_2025-12_001-004_Contents.pdf (material_kind=contents)
  - Mg_2025-12_005-005_Editorial.pdf (material_kind=editorial)
  - Mg_2025-12_016-027_Burykina.pdf (from ru_authors_author_translit)
  - Mg_2025-12_067-073_Zaklyazminskaya.pdf (from ru_authors_translit)
  - Mg_2025-12_110-112_Bragina.pdf (ru_title separation fixed)

**Documentation:**
- Policy: docs/policies/filename_generation_policy_v_1_0.md (referenced in implementation)
- GATE-0 Proof: GATE0_PROOF.md

## 2026-02-06
- **Grenaderova article split bugfix (Mg_2026-01):**
  - Issue: Article "Grenaderova" (pages 27-36) incorrectly split into two files (027-027, 028-036)
  - Root cause: BoundaryDetector dedup ratio calculation bug — compared only first typography candidate per page (92/37 = 2.486 > 2.0 threshold) instead of sum of all candidates
  - Evidence: RUN_DIR artifacts (03.json anchors, 04.json boundaries) showed multi-line RU title (4 candidates: 37,35,54,35 chars) vs EN title (2 candidates: 92,72 chars)
  - Fix: detector.py lines 241-244 — changed dedup to sum all candidates per page (161 vs 164 chars, ratio 1.019 < 2.0 ✅)
  - Commit: 55e0f08 — fix(boundary): dedup ratio calculation for multi-line titles
  - Verification: Re-run confirmed T=L=E=8 (was 9), single file Mg_2026-01_027-036_Grenaderova.pdf (207K), 7 other files unchanged
  - Export: /srv/pdf-extractor/exports/Mg/2026/Mg_2026-01/exports/2026_02_06__19_12_02/
  - Regression validation: Compared 9 files (before) vs 8 files (after), only Grenaderova changed as expected

## 2026-03-31

- **RU single-initial byline fix in MetadataExtractor v1.3.3 (Mh_2026-03 trigger):**
  - Issue-триггер: выпуск Mh_2026-03 выявил три ошибки именования файлов
  - Ошибочные filenames устранены:
    - `Mh_2026-03_033-039_Analiziruya.pdf` → `Mh_2026-03_033-039_Vasilkova.pdf` (running header «Том 21, № 3» принимался за ru_authors)
    - `Mh_2026-03_055-066_Skim.pdf` → `Mh_2026-03_055-066_Plotkin.pdf` (фрагмент тела статьи принимался за ru_authors)
    - `Mh_2026-03_067-070_Editorial.pdf` → `Mh_2026-03_067-070_Gelprin.pdf` (single-initial автор «Гелприн М.» не проходил AUTH_INITIALS_RE → BoundaryDetector ошибочно классифицировал как editorial)
  - Уровень fix'а: MetadataExtractor `_pick_ru_authors` — extractor-level author detection
  - Решение: negative gate `is_running_header()` + positive gate `looks_like_author_byline()` / `looks_like_single_initial_byline()` / `extract_single_initial_byline_prefix()` вместо прежнего `"," in text or AUTH_INITIALS_RE`
  - EN false-positive risk: при добавлении `_at_start` в `_pick_en_authors` обнаружен regression — «Lana R. Dzik;» принималась за single-initial byline (Mg_2025-12 p68). `_at_start` из EN-path убран; `TOP_REGION_FRAC=0.40` сохранён как guardrail.
  - Валидация: T=L=E=9 (sha256 verified); тесты +93 (unit tests в `tests/unit/`)
  - Commits: c9d1df5 (byline gating), ede3839 (prefix extraction)
  - Policy: `docs/policies/filename_generation_policy_v_1_3.md`

## 2026-04-01

- **Mg_2026-03 production validation:**
  - T=L=E=9 (1 Contents + 8 Research), sha256 verified
  - Обработан через Phase 3 Web UI
  - Export: `/srv/pdf-extractor/exports/Mg/2026/Mg_2026-03/`

## 2026-04-04

- **BoundaryDetector v1.3.2 (commit ed0c677):**
  - Fix: `_has_contents_marker` — abs-window заменён на forward-only
  - Причина: ложная Contents-классификация при наличии `contents_marker` в нестандартной позиции anchor-list
  - Validation: Na_2026-03 T=L=E=7 ✅

- **Na_2026-03 production validation:**
  - T=L=E=7 (1 Contents + 1 Editorial + 4 Research + 1 Digest), sha256 verified
  - Обработан через Phase 3 Web UI
  - Первый production-confirmed Digest file: `Na_2026-03_056-094_Digest.pdf`
  - ru_title: «Дайджест англоязычной отраслевой периодики»

- **Phase 3 Web UI опубликован публично:**
  - URL: `https://pdf-extractor.irdimas.ru`
  - Stack: nginx + Let's Encrypt + Basic Auth (user=dmitry) + Cloudflare proxy

## 2026-04-05

- **BoundaryDetector v1.3.3 (commit 79466eb):**
  - Добавлен `_has_digest_title(ru_title: str) -> bool`
  - Семантический fix: editorial → digest когда `ru_title.startswith(("Дайджест", "Digest"))`
  - Проверяется в `_classify_material_kind()` перед `return "editorial"` — приоритет над editorial fallback
  - Validation: pytest 153/153 ✅, golden 28/28 ✅, material classification 29/29 EXACT MATCH ✅

- **UI Hardening Pass v1 (commit 3e93a52):**
  - `_plural_articles` Jinja2 filter (русское склонение «статья/статьи/статей»)
  - footer Phase 3 в `ui/templates/base.html`
  - `ui/templates/history.html`: локализация статусов + ZIP download button
  - `ui/templates/partials/status_card.html`: pid removed, plural, sha256 Windows hint

- **UI Hardening Pass v2 (commit f3f10be):**
  - `_read_log_tail(log_path, n=25)` в `ui/main.py` — читает `[step N/8]` строки из лога pipeline
  - Блок «Прогресс» в status_card RUNNING секции
  - HTMX poll каждые 2с обновляет progress в реальном времени

- **HTMX SRI hash fix (commit 5dc40ec):**
  - Root cause: неверный SRI hash в `ui/templates/base.html` блокировал htmx.js → polling не работал
  - Fix: hash исправлен на `sha384-D1Kt99CQMDuVetoL1lrYwg5t+9QdHe7NLX/SoJYkXDFfX37iInKRy5xLSi8nO7UC`
  - Верифицировано в production: polling requests каждые 2с, progress виден без ручного refresh

- **BoundaryDetector design doc v_1_4 создан** (`docs/design/pdf_extractor_boundary_detector_v_1_4.md`):
  - Документирован v1.3.2 forward-only window fix (§3.6.1)
  - Документирован v1.3.3 `_has_digest_title()` детерминированное правило (§3.6.3)
