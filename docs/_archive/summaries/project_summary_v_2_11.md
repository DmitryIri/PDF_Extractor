# Project Summary — PDF Extractor

**Version:** v_2_11
**Status:** Canonical
**Date:** 2026-02-04

---

## 1. Назначение документа

Project Summary — это **канонический снимок состояния проекта** на конкретную дату. Документ фиксирует:
- текущее архитектурное и функциональное состояние;
- утверждённые канонические артефакты;
- активный этап работ;
- границы ответственности и источники истины.

Документ **не является**:
- журналом изменений;
- логом сессии;
- историей коммитов.

Каждая новая версия Project Summary **сохраняет структуру** и обновляется только по факту изменения состояния проекта.

---

## 2. Границы проекта

**PDF Extractor** — детерминированный Python-based pipeline для автоматической обработки выпусков научных журналов (PDF) с целью:
- извлечения наблюдаемых фактов (anchors);
- детерминированного определения границ статей;
- физического разрезания PDF;
- проверки и сборки финальных артефактов.

Проект спроектирован по принципам:
- code-first;
- facts only;
- отсутствие неявных эвристик;
- воспроизводимость результата;
- строгие контракты между компонентами.

---

## 3. Каноническая архитектура

Pipeline выполняется строго последовательно:
1. InputValidator
2. PDFInspector
3. MetadataExtractor (FULL PDF)
4. BoundaryDetector
5. Splitter
6. MetadataVerifier
7. OutputBuilder
8. OutputValidator ✅

Каждый компонент:
- изолирован;
- не знает о n8n;
- принимает JSON через stdin;
- возвращает JSON через stdout;
- завершает работу детерминированным exit-code.

---

## 4. Текущее состояние реализации (As-Is)

**Активная фаза:** Universal Surname Selection Fix — ✅ ЗАВЕРШЕНА → Phase 3 (UI/DB) в подготовке

### Завершённые milestones

#### Phase 0: Infrastructure
- ✅ Python venv setup
- ✅ Runtime/code separation (`/opt/projects/` vs `/srv/`)

#### Phase 1: Quality Diagnostics + Golden Test
- ✅ Anchors quality diagnostics (ru_* noise analysis completed)
- ✅ Typography extraction capability validated (MyriadPro-BoldIt 12pt)
- ✅ Golden Test created and validated:
  - Issue: mg_2025_12
  - Total articles: 29 (1 Contents + 1 Editorial + 27 Research)
  - Precision: 100%
  - Recall: 100%
  - F1-score: 100%

#### Phase 2: Core Pipeline Components
- ✅ InputValidator — реализован и принят
- ✅ PDFInspector — реализован и принят
- ✅ MetadataExtractor — реализован (v_1_0.1), извлекает anchors по всему PDF (DOI + text_block с bbox)
- ✅ BoundaryDetector — реализован (v_1_2), детерминированное определение границ статей по typography
- ✅ Splitter — реализован, физическая разрезка PDF по boundary_ranges
- ✅ MetadataVerifier — реализован (v_1_3_0), верификация и обогащение manifest
- ✅ OutputBuilder — реализован, экспорт статей на FS с canonical naming
- ✅ OutputValidator — реализован, финальная валидация T=L=E инварианта

#### Universal Surname Selection Fix (Plan-03) — 2026-02-04
- ✅ Running-header filter (Vol/Tom/Том) — universal, no journal/issue hardcodes
- ✅ STEP A→B→C surname extraction algorithm
- ✅ GOST rule 3: word-final ый → yi (Безчасный → Bezchasnyi)
- ✅ TOC re-verification by anchors (contents_marker in article's own page range)
- ✅ text_block fallback (STEP C): N=6 byline-candidate budget, 2-initial regex, HARD/SOFT stopwords
- ✅ Shared module: `shared/author_surname_normalizer.py` (pure functions)
- ✅ Unit tests: 88/88 pass
- ✅ Mg golden regression: byte-for-byte match (29 articles)
- ✅ Mh_2026-01 acceptance: all 9 filenames correct
- ✅ Policy: FilenameGeneration v_1_1 (GOST rule 3, STEP C, TOC re-verification)
- DEVIATION: N=6 counts byline-pattern candidates only (not all text_blocks in window)

### Блокеры
Нет активных блокеров.

---

## 5. Канонические документы проекта

### TechSpec
- PDF Extractor — TechSpec v_2_6 (Canonical) — committed
  - Stdin envelope + stdout/stderr contract
  - Typography-based detection specification
  - Rich article_starts schema
  - OutputValidator specification (§7.8)

### Plan
- PDF Extractor — Plan v_2_4 (Canonical) — acceptance: confidence == 1.0 (binary match), rich `article_starts` objects; supersedes v_2_3

### Component Design Documents
- BoundaryDetector v_1_1 (Canonical) — committed
  - Typography-based PRIMARY SIGNAL (MyriadPro-BoldIt, 12.0 ± 0.5)
  - Fixed confidence=1.0 (deterministic binary match)

### Policies
- ArticleStartDetection Policy v_1_0 (Canonical)
- FilenameGeneration Policy v_1_0 (Canonical) — superseded by v_1_1
- FilenameGeneration Policy v_1_1 (Canonical) — GOST rule 3, STEP C text_block fallback, TOC re-verification

### Golden Tests
- `golden_tests/mg_2025_12_article_starts.json`
- `golden_tests/mg_2025_12_anchors.json`
- `golden_tests/mg_2025_12_boundaries.json`
- `golden_tests/mg_2025_12_splitter_output.json`

### Governance / Meta
- canonical_artifact_registry.md
- context_bootstrap_protocol.md
- session_closure_protocol.md
- session_finalization_playbook.md
- documentation_rules_style_guide.md
- versioning_policy.md
- project_files_index.md (v_1_7)

---

## 6. Source of Truth

**Единый источник истины:** Git-репозиторий
`/opt/projects/pdf-extractor`

- `agents/` — код core-компонентов
- `shared/` — shared pure-function modules (author_surname_normalizer)
- `docs/` — TechSpec, Plan, policies, summaries
- `golden_tests/` — ground truth для regression testing
- `tests/` — unit и integration тесты
- `tools/` — universal pipeline runner (run_issue_pipeline.sh)
- runtime-артефакты не считаются источником истины

---

## 7. Инварианты состояния

### Architectural Invariants
- MetadataExtractor не фильтрует anchors (возвращает raw observations)
- BoundaryDetector обязан строго следовать ArticleStartPolicy
- Confidence считается детерминированно
- Одиночный сигнал (например, DOI) не может быть решающим
- T = L = E инвариант: количество статей в JSON = количество имен файлов = количество реальных PDF (enforced by OutputValidator)
- MetadataVerifier не содержит issue/journal/page_range hardcodes (enforced by FilenameGeneration Policy v_1_1)

### Validated Detection Rules (mg_2025_12)
- **PRIMARY signal:** Typography marker (MyriadPro-BoldIt, 12pt) достаточен для detection
- **FILTER required:** Language-based duplicate detection (билингвальная RU/EN структура)
- **ACCEPTANCE threshold:** Precision >= 90%, Recall >= 80% (achieved: 100%/100%)

### Edition-Specific
- Журнал "Медицинская генетика" использует билингвальную структуру:
  - RU блок (title, authors, affiliations, abstract)
  - EN блок (title, authors, affiliations, abstract) на следующей странице
- Рубрики используют отличный шрифт: MyriadPro-BoldCond, 14pt (vs MyriadPro-BoldIt, 12pt для статей)

### Export Structure Invariants
- Экспортная иерархия: `/srv/pdf-extractor/exports/{JournalCode}/{YYYY}/{IssuePrefix}/exports/{export_id}/`
- Atomic export: сборка в `{export_id}.tmp/` → atomic rename в `{export_id}/`
- Naming rule: `{IssuePrefix}_{PPP-PPP}_{FirstAuthorSurname}.pdf` (PPP = 3-digit zero-padded page numbers)
- Обязательные файлы в export package: `articles/`, `manifest/export_manifest.json`, `checksums.sha256`, `README.md`

### Validation Invariants
- **T=L=E invariant:** total_articles == len(articles) == count(PDF files) — строгое равенство, без толерантности
- **3-way checksum verification:** computed SHA256 = stdin checksum = checksums.sha256 file = manifest checksum
- **Filename policy compliance:** все filenames соответствуют FilenameGenerationPolicy v_1_1 (research / service patterns)
- **Unwrap pattern:** OutputValidator принимает как envelope format, так и raw data format

---

## 8. Принятые решения

### D1: Typography Marker as PRIMARY Signal (2026-01-13)
**Решение:** MyriadPro-BoldIt, 12pt достаточен как PRIMARY signal для article start detection.
**Обоснование:** Golden Test mg_2025_12: Precision 100%, Recall 100%.

### D2: Language-Based Duplicate Filter (2026-01-13)
**Решение:** Применять proximity filter с language detection для фильтрации EN-дубликатов.
**Обоснование:** Билингвальная структура журнала (RU + EN на соседних страницах).

### D3: Golden Test as Canonical Ground Truth (2026-01-13)
**Решение:** `mg_2025_12_article_starts.json` является canonical reference для regression testing.

### D4: Canonical Export Structure (2026-01-23)
**Решение:** FS-only export structure без DB/UI.
**Структура:** `/srv/pdf-extractor/exports/{JournalCode}/{YYYY}/{IssuePrefix}/exports/{export_id}/`

### D5: 3-Way Checksum Verification (2026-01-27)
**Решение:** OutputValidator проверяет SHA256 checksums из трёх источников: computed, stdin, checksums.sha256 file.

### D6: N=6 Candidate Budget (2026-02-04)
**Решение:** STEP C scan limit N=6 считает только byline-pattern кандидаты, не все text_blocks в окне. Running headers и structural noise прозрачны для счётчика.
**Обоснование:** MetadataExtractor выдаёт 60+ text_blocks/page (page numbers, section titles, journal names). Byline может быть 14-м+ text_block на странице. Candidate budget сохраняет safety bound (≤6 surname evaluations) без зависимости от anchor-list ordering.

---

## 9. Открытые вопросы / риски

### Открытые вопросы
**Q1: Источник first_author_surname** — ✅ RESOLVED
Реализован в MetadataVerifier v1.3.0: STEP A (ru_authors + en_authors) → STEP B (en_authors) → STEP C (text_block fallback). Все источники задокументированы в FilenameGeneration Policy v_1_1 §4 + §7.

**Q2: Политика повторных экспортов**
**Статус:** 🟡 Не реализовано
**Описание:** Как инкрементировать `export_id` при повторных экспортах одного и того же issue.
**Варианты:** временная метка (текущая реализация), счётчик версий.

**Q3: STEP D (deterministic fallback)**
**Статус:** 🟡 Отложен
**Описание:** Формат «Axx» блокируется OutputValidator regex `[A-Z][a-z]+` и `_validate_surname_en`. Требует scope change в OutputValidator. Для Mg и Mh: unreachable (все статьи разрешены STEP A/B/C).

### Риски
Нет активных рисков.

---

## 10. Следующий шаг

**Core Pipeline:** ✅ Все 8 компонентов завершены + Universal Surname Selection Fix

**Next Phase: Phase 3 — UI/DB**
- Bootstrap stub: `docs/governance/task_specs/task_spec_phase_3_ui_db_bootstrap_v_1_0.md`
- Goal: UI upload → pipeline run → download zip
- DB: store runs / manifests / artifacts
- Decision points pending: DB backend, auth, storage
- Требуется: full Plan (отдельный CC session)

---

## 11. CHANGELOG

### v_2_11 — 2026-02-04
- **Universal Surname Selection Fix (Plan-03) завершён:**
  - MetadataVerifier v1.3.0: STEP A→B→C, running-header filter, GOST rule 3 (ый→yi), TOC re-verification
  - Shared module: `shared/author_surname_normalizer.py`
  - Unit tests: 88/88 pass — `tests/unit/test_author_surname_normalizer.py`
  - Policy: FilenameGeneration v_1_1 (GOST rule 3, STEP C, TOC re-verification, N=6 candidate budget)
  - Acceptance: A1–A8 all PASS; Mg golden byte-for-byte; Mh 9/9 filenames correct
  - DEVIATION: N=6 counts byline-pattern candidates (not all text_blocks) — see D6
- **Documentation:**
  - project_summary_v_2_10 → v_2_11
  - project_files_index v_1_6 → v_1_7 (filename_generation_policy registered)
  - project_history_log updated (2026-02-04 entry)
  - execution_report_2026_02_04_universal_surname_selection_fix.md created
- **Phase 3 bootstrap:**
  - Created `docs/governance/task_specs/task_spec_phase_3_ui_db_bootstrap_v_1_0.md`
- **Q1 resolved:** first_author_surname source extraction fully implemented (STEP A/B/C)
- **Decision D6 recorded:** N=6 candidate budget semantics

### v_2_10 — 2026-01-27
- Phase 2.8 OutputValidator завершён
- Все 8 core-компонентов завершены

### v_2_9 — 2026-01-26
- Phase 2.7 OutputBuilder завершён

### v_2_8 — 2026-01-22
- Documentation alignment completed: TechSpec v_2_5, Plan v_2_3, BoundaryDetector v_1_1

### v_2_7 — 2026-01-15
- Синхронизация с Plan v_2_4

### v_2_6 — 2026-01-15
- Phase 1 завершена: Quality diagnostics + Golden Test validation
