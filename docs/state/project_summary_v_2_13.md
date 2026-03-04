# Project Summary — PDF Extractor

**Version:** v_2_13
**Status:** Canonical
**Date:** 2026-03-04

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

**Активная фаза:** Phase 2 полностью завершена (включая run-pipeline AC1-AC7, Mg_2026-01, Mh_2026-02, Na_2026-02 production processing) → Phase 3 (UI/DB) в подготовке

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
- ✅ InputValidator — реализован и принят (v1.0.0)
- ✅ PDFInspector — реализован и принят (v1.0.0)
- ✅ MetadataExtractor — реализован (v1.3.2), извлекает anchors по всему PDF (DOI + text_block с bbox); fix: contents_marker length filter
- ✅ BoundaryDetector — реализован (v1.3.1), детерминированное определение границ статей; fix: info detection + DOI check
- ✅ Splitter — реализован (v1.0.0), физическая разрезка PDF по boundary_ranges
- ✅ MetadataVerifier — реализован (v1.4.0), верификация и обогащение manifest; fix: info material_kind support
- ✅ OutputBuilder — реализован (v1.2.0), экспорт статей на FS с canonical naming; fix: info material_kind support
- ✅ OutputValidator — реализован (v1.0.0), финальная валидация T=L=E инварианта

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

#### info material_kind — 2026-02-21
- ✅ BoundaryDetector v1.3.1: standalone «ИНФОРМАЦИЯ»/«INFORMATION» text_block AND no DOI on page → `info`
- ✅ Отличие от research с рубрикой «ИНФОРМАЦИЯ»: у research есть article-level DOI
- ✅ Filename: `{IssuePrefix}_{PPP-PPP}_Info.pdf`
- ✅ Поддержан всем pipeline: detector → verifier → builder → validator
- ✅ Policy: FilenameGeneration v_1_2

#### Mh_2026-02 Production Validation — 2026-02-21
- ✅ T=L=E=9 (1 Contents + 7 Research + 1 Info), sha256 verified
- ✅ Export: `/srv/pdf-extractor/exports/Mh/2026/Mh_2026-02/exports/2026_02_21__19_04_46/`
- ✅ Fixes: MetadataExtractor v1.3.2, BoundaryDetector v1.3.1, MetadataVerifier v1.4.0, OutputBuilder v1.2.0

#### Na_2026-02 Production Validation — 2026-03-04
- ✅ T=L=E=6 (1 Contents + 4 Research + 1 Editorial), sha256 verified
- ✅ Export: `/srv/pdf-extractor/exports/Na/2026/Na_2026-02/exports/2026_03_04__14_39_05/`
- ✅ Журнал «Наркология» — первый выпуск, обработан без изменений кода

### Блокеры
Нет активных блокеров.

---

## 5. Канонические документы проекта

### TechSpec
- PDF Extractor — TechSpec v_2_8 (Canonical) — committed
  - Stdin envelope + stdout/stderr contract
  - Typography-based detection specification
  - Rich article_starts schema
  - OutputValidator specification (§7.8)
  - §6.4: inbox/ — canonical input path с политикой хранения/очистки (RFC-4)
- PDF Extractor — TechSpec v_2_7 (superseded by v_2_8) — immutable

### Plan
- PDF Extractor — Plan v_2_5 (Canonical) — supersedes v_2_4; добавлен info material_kind, refs → TechSpec v_2_7

### Component Design Documents
- BoundaryDetector v_1_3 (Canonical) — committed
  - Typography-based PRIMARY SIGNAL (MyriadPro-BoldIt, 12.0 ± 0.5)
  - Fixed confidence=1.0 (deterministic binary match)
  - info material_kind detection

### Policies
- ArticleStartDetection Policy v_1_0 (Canonical)
- FilenameGeneration Policy v_1_0 (Canonical) — superseded by v_1_1
- FilenameGeneration Policy v_1_1 (Canonical) — superseded by v_1_2
- FilenameGeneration Policy v_1_2 (Canonical) — info material_kind (_Info.pdf suffix)

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
- project_files_index.md (v_1_9)

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
- MetadataVerifier не содержит issue/journal/page_range hardcodes (enforced by FilenameGeneration Policy v_1_2)

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
- **Filename policy compliance:** все filenames соответствуют FilenameGenerationPolicy v_1_2 (research / service patterns incl. info)
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

### D7: Timestamp-Based export_id (2026-03-04)
**Решение:** export_id = UTC timestamp `YYYY_MM_DD__HH_MM_SS`. Повторные прогоны одного выпуска создают новые директории (не перезаписывают).
**Обоснование:** Детерминизм + аудитабельность: каждый run имеет уникальный путь. Подтверждено: Na_2026-02 обработан дважды в одной сессии, оба экспорта сохранены.

---

## 9. Открытые вопросы / риски

### Открытые вопросы
**Q1: Источник first_author_surname** — ✅ RESOLVED
Реализован в MetadataVerifier v1.4.0: STEP A (ru_authors + en_authors) → STEP B (en_authors) → STEP C (text_block fallback). Все источники задокументированы в FilenameGeneration Policy v_1_2 §4 + §7.

**Q2: Политика повторных экспортов** — ✅ RESOLVED
Timestamp-based export_id (D7). Повторные прогоны создают новые директории — не перезаписывают предыдущие. Подтверждено в production (Na_2026-02, 2026-03-04).

**Q3: STEP D (deterministic fallback)**
**Статус:** 🟡 Отложен
**Описание:** Формат «Axx» блокируется OutputValidator regex `[A-Z][a-z]+` и `_validate_surname_en`. Требует scope change в OutputValidator. Для Mg, Mh, Na: unreachable (все статьи разрешены STEP A/B/C).

### Риски
Нет активных рисков.

---

## 10. Следующий шаг

**Core Pipeline:** ✅ Все 8 компонентов завершены + Universal Surname Selection Fix + info material_kind

**Production validated journals:** Mg (2025-12, 2026-01), Mh (2026-01, 2026-02), Na (2026-02)

**Next Phase: Phase 3 — UI/DB**
- Bootstrap stub: `docs/governance/task_specs/task_spec_phase_3_ui_db_bootstrap_v_1_0.md`
- Goal: UI upload → pipeline run → download zip
- DB: store runs / manifests / artifacts
- Decision points pending: DB backend, auth, storage
- Требуется: full Plan (отдельный CC session)

---

## 11. CHANGELOG

### v_2_13 (updated) — 2026-03-04
- **RFC-4:** TechSpec v_2_7 → v_2_8 (canonical): §6.4 inbox/ как canonical input path (naming, scp delivery, retention policy, data flow); project_files_index v_1_10 → v_1_11

### v_2_13 — 2026-03-04
- **Component versions updated (facts):**
  - MetadataExtractor: v1.0.1 → v1.3.2 (contents_marker length filter)
  - BoundaryDetector: v1.2 → v1.3.1 (info detection + DOI check)
  - MetadataVerifier: v1.3.0 → v1.4.0 (info material_kind support)
  - OutputBuilder: → v1.2.0 (info material_kind support)
- **New milestones:**
  - info material_kind: standalone ИНФОРМАЦИЯ/INFORMATION без DOI → `info`, suffix `_Info.pdf`
  - Mh_2026-02: T=L=E=9, sha256 OK (2026-02-21)
  - Na_2026-02: T=L=E=6, sha256 OK (2026-03-04) — журнал «Наркология», первый выпуск
- **Canonical docs updated:**
  - TechSpec v_2_6 → v_2_7
  - BoundaryDetector design v_1_2 → v_1_3
  - Plan v_2_4 → v_2_5
  - FilenameGeneration Policy v_1_1 → v_1_2 (canonical)
  - project_files_index v_1_8 → v_1_9
- **Q2 resolved:** Timestamp-based export_id confirmed in production (D7 added)
- **project_summary_v_2_11 archived** to `docs/_archive/summaries/`

### v_2_12 — 2026-02-06
- **Documentation sync:**
  - Plan v_2_4 synchronized with TechSpec v_2_6 (version references, BoundaryDetector schema, material classification, MetadataVerifier enrichment)
  - BoundaryDetector v_1_1 → v_1_2 (canonical version updated)
  - project_files_index v_1_7 → v_1_8 (canonical version updated)
  - project_history_log updated (2026-02-06 Grenaderova bugfix entry)
- **Phase status updated:**
  - Phase 2 полностью завершена (включая run-pipeline AC1-AC7, Mg_2026-01 issue processing)
- **Grenaderova bugfix (2026-02-06):**
  - Issue: Multi-line RU title split detection (pages 27-36 split into 2 files)
  - Fix: BoundaryDetector dedup ratio calculation (sum all candidates per page)
  - Commit: 55e0f08
  - Export: /srv/pdf-extractor/exports/Mg/2026/Mg_2026-01/exports/2026_02_06__19_12_02/ (T=L=E=8)

### v_2_11 — 2026-02-04
- Universal Surname Selection Fix (Plan-03) завершён
- MetadataVerifier v1.3.0: STEP A→B→C, running-header filter, GOST rule 3, TOC re-verification
- Policy: FilenameGeneration v_1_1

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
