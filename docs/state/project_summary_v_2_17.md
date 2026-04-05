# Project Summary — PDF Extractor

**Version:** v_2_17
**Status:** Canonical
**Date:** 2026-04-05

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

**Активная фаза:** Phase 2 полностью завершена; Phase 3 (Web UI) — задеплоено и опубликовано

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
- ✅ MetadataExtractor — реализован (v1.3.3), извлекает anchors по всему PDF (DOI + text_block с bbox); fix: running-header exclusion + byline gating + single-initial support (RU)
- ✅ BoundaryDetector — реализован (v1.3.3), детерминированное определение границ статей; fix: info detection + DOI check + forward-only window (v1.3.2) + digest detection by ru_title (v1.3.3)
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

#### Phase 3: Web UI — MVP задеплоено (2026-03-04)
- ✅ Stack: FastAPI + Tailwind CDN + HTMX CDN + SQLite + asyncio subprocess
- ✅ Код: `ui/` (main.py, db.py, pipeline.py, templates/)
- ✅ Сервис: `systemctl status pdf-extractor-ui` (127.0.0.1:8080)
- ✅ SSH tunnel с PC: `ssh -L 18080:localhost:8080 dmitry@2.58.98.101` → http://localhost:18080
- ✅ DB: `/srv/pdf-extractor/db/runs.db`; Логи: `/srv/pdf-extractor/logs/ui_runs/`
- ✅ UI: upload PDF → выбор журнала/выпуска → запуск pipeline → скачать ZIP
- ✅ ZIP содержит: articles/ + manifest/export_manifest.json + checksums.sha256 + README.md
- 🟡 Acceptance testing (AC1–AC7) с реальным PDF — pending (Q7)

#### Mg_2026-02 Production Validation — 2026-03-11
- ✅ T=L=E=11 (1 Contents + 10 Research), sha256 verified
- ✅ Обработан через Phase 3 Web UI (http://localhost:18080) — первый production run через UI
- ✅ Верифицирован пользователем

#### Upwork Portfolio Assets — 2026-03-05
- ✅ `README.md` — переработан: английский, Pipeline at a glance (ASCII 8 агентов), Outputs, Quality gates, Web UI, Security note
- ✅ `docs/portfolio/architecture.md` — ASCII pipeline diagram + production validation table
- ✅ `docs/portfolio/screenshots_plan.md` — guide: 3 скрина для Upwork
- ✅ `docs/portfolio/upwork_project_1_description.md` — текст проекта для Upwork (7 production runs, 79 articles)
- ✅ Security scan: OK to go public (commit c9205fe)

#### RU Single-Initial Byline Fix (MetadataExtractor v1.3.3) — 2026-03-31
- ✅ Negative gate: `is_running_header()` — исключает running headers из `_pick_ru_authors`
- ✅ Positive gate: `looks_like_author_byline()` (2-initial) + `looks_like_single_initial_byline()` (1-initial, RU)
- ✅ Prefix extraction: `extract_single_initial_byline_prefix()` для merged blocks («Гелприн М. Рассказ...» → «Гелприн М.»)
- ✅ EN-path guardrail: `_at_start` исключён из `_pick_en_authors` (empirical false-positive на Mg_2025-12 p68); `TOP_REGION_FRAC=0.40` сохранён
- ✅ Unit tests: +93 теста (`test_author_surname_normalizer.py` + `test_metadata_extractor_pick_authors.py`)
- ✅ Policy: FilenameGeneration v_1_3

#### Mh_2026-03 Production Validation — 2026-03-31
- ✅ T=L=E=9, sha256 verified
- ✅ Export: `/srv/pdf-extractor/exports/Mh/2026/Mh_2026-03/exports/2026_03_31__19_33_33/`
- ✅ Исправлены 3 ошибки именования: Vasilkova (было Analiziruya), Plotkin (было Skim), Gelprin (было Editorial)

#### BoundaryDetector digest fix + forward-only window — 2026-04-04/05
- ✅ BoundaryDetector v1.3.2 (commit ed0c677): `_has_contents_marker` forward-only window — устранён false Contents при нестандартном anchor порядке
- ✅ BoundaryDetector v1.3.3 (commit 79466eb): `_has_digest_title()` — детерминированное правило: `ru_title.startswith(("Дайджест", "Digest"))` → `material_kind=digest`, проверяется перед editorial fallback
- ✅ Validation: pytest 153/153 ✅, golden 28/28 ✅, material classification 29/29 EXACT MATCH ✅

#### Mg_2026-03 Production Validation — 2026-04-01
- ✅ T=L=E=9 (1 Contents + 8 Research), sha256 verified
- ✅ Обработан через Phase 3 Web UI

#### Na_2026-03 Production Validation — 2026-04-04
- ✅ T=L=E=7 (1 Contents + 1 Editorial + 4 Research + 1 Digest), sha256 verified
- ✅ Первый production-confirmed Digest file: `Na_2026-03_056-094_Digest.pdf`
- ✅ BoundaryDetector v1.3.2 + v1.3.3 валидированы в production

#### Phase 3 Web UI — Production Hardening (2026-04-05)
- ✅ UI Hardening Pass v1: `_plural_articles` Jinja2 filter; footer Phase 3; history локализация + ZIP download; status_card: plural, sha256 hint
- ✅ UI Hardening Pass v2: `_read_log_tail(log_path, n=25)` helper; блок «Прогресс» в RUNNING секции; HTMX poll каждые 2с
- ✅ HTMX SRI hash fix: исправлен SRI hash для htmx@1.9.10 → polling работает без ручного refresh (root cause: SRI mismatch блокировал htmx.js)
- ✅ Публичный URL: `https://pdf-extractor.irdimas.ru` (nginx + Let's Encrypt + Basic Auth + Cloudflare)

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
- BoundaryDetector v_1_4 (Canonical) — committed
  - Typography-based PRIMARY SIGNAL (MyriadPro-BoldIt, 12.0 ± 0.5)
  - Fixed confidence=1.0 (deterministic binary match)
  - info material_kind detection
  - forward-only window в `_has_contents_marker` (v1.3.2)
  - digest detection by ru_title prefix `_has_digest_title()` (v1.3.3)
- BoundaryDetector v_1_3 (superseded by v_1_4) — immutable

### Policies
- ArticleStartDetection Policy v_1_0 (Canonical)
- FilenameGeneration Policy v_1_0 (Canonical) — superseded by v_1_1
- FilenameGeneration Policy v_1_1 (Canonical) — superseded by v_1_2
- FilenameGeneration Policy v_1_2 (Canonical) — superseded by v_1_3
- FilenameGeneration Policy v_1_3 (Canonical) — RU single-initial byline support (§4.7); EN-path guardrail documented

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
- project_files_index.md (v_1_21)

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
- `ui/` — Phase 3 Web UI (FastAPI, db, pipeline runner, templates)
- `docs/portfolio/` — Upwork portfolio assets (architecture diagram, screenshots plan, project description)
- runtime-артефакты не считаются источником истины

---

## 7. Инварианты состояния

### Architectural Invariants
- MetadataExtractor не фильтрует anchors (возвращает raw observations)
- BoundaryDetector обязан строго следовать ArticleStartPolicy
- Confidence считается детерминированно
- Одиночный сигнал (например, DOI) не может быть решающим
- T = L = E инвариант: количество статей в JSON = количество имен файлов = количество реальных PDF (enforced by OutputValidator)
- MetadataVerifier не содержит issue/journal/page_range hardcodes (enforced by FilenameGeneration Policy v_1_3)

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
- **Filename policy compliance:** все filenames соответствуют FilenameGenerationPolicy v_1_3 (research / service patterns incl. info)
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

### D8: Web UI as Phase 3 MVP (2026-03-04)
**Решение:** FastAPI + Tailwind CDN + HTMX CDN + SQLite — минимальный стек без Node.js/npm.
**Обоснование:** Zero build-step frontend (CDN), Python-only backend соответствует проектному принципу. SQLite достаточен для solo-use.

---

## 9. Открытые вопросы / риски

### Открытые вопросы
**Q1: Источник first_author_surname** — ✅ RESOLVED
Реализован в MetadataVerifier v1.4.0: STEP A (ru_authors + en_authors) → STEP B (en_authors) → STEP C (text_block fallback). Все источники задокументированы в FilenameGeneration Policy v_1_3 §4 + §7.

**Q2: Политика повторных экспортов** — ✅ RESOLVED
Timestamp-based export_id (D7). Повторные прогоны создают новые директории — не перезаписывают предыдущие. Подтверждено в production (Na_2026-02, 2026-03-04).

**Q3: STEP D (deterministic fallback)**
**Статус:** 🟡 Отложен
**Описание:** Формат «Axx» блокируется OutputValidator regex `[A-Z][a-z]+` и `_validate_surname_en`. Требует scope change в OutputValidator. Для Mg, Mh, Na: unreachable (все статьи разрешены STEP A/B/C).

**Q7: UI AC1–AC7 acceptance testing**
**Статус:** 🟡 Pending
**Описание:** Полное acceptance testing Phase 3 Web UI с реальным PDF через `https://pdf-extractor.irdimas.ru`. AC1–AC7 по аналогии с run-pipeline skill.

**Q8: GitHub repo public vs portfolio fork**
**Статус:** 🟡 Pending
**Описание:** Решить: сделать ли GitHub repo public (IP 2.58.98.101 в techspec — не credential, не блокер) или создать отдельный public portfolio fork с заменой IP на placeholder.

### Риски
Нет активных рисков.

---

## 10. Следующий шаг

**Core Pipeline:** ✅ Все 8 компонентов завершены + Universal Surname Selection Fix + info material_kind + digest detection

**Production validated journals:** Mg (2025-12, 2026-02, 2026-03), Mh (2026-02, 2026-03), Na (2026-02, 2026-03) — 7 runs total, 79 articles

**Phase 3 Web UI:** ✅ Задеплоено и опубликовано — `https://pdf-extractor.irdimas.ru`

**Pending:**
- Q7: UI AC1–AC7 acceptance testing через публичный URL
- Q8: GitHub public vs portfolio fork — принять решение
- Upwork: загрузить 3 скрина по `docs/portfolio/screenshots_plan.md`

---

## 11. CHANGELOG

### v_2_17 — 2026-04-05
- **BoundaryDetector v1.3.2:** `_has_contents_marker` forward-only window fix — устранён false Contents classification
- **BoundaryDetector v1.3.3:** `_has_digest_title()` — детерминированное digest detection rule по ru_title prefix
- **Mg_2026-03 production validation:** T=L=E=9, sha256 OK (2026-04-01)
- **Na_2026-03 production validation:** T=L=E=7, sha256 OK; первый production Digest file (2026-04-04)
- **Phase 3 UI Hardening Pass v1+v2:** progress visibility, plural filter, ZIP download, HTMX SRI fix
- **Public URL:** `https://pdf-extractor.irdimas.ru` (задеплоено 2026-04-04)
- **BoundaryDetector design:** v_1_3 → v_1_4 (canonical)
- **project_files_index:** v_1_20 → v_1_21
- **project_summary_v_2_16** → superseded by v_2_17

### v_2_16 — 2026-03-31
- **MetadataExtractor v1.3.3:** running-header exclusion + byline gating + single-initial byline support (RU path); EN-path guardrail (TOP_REGION_FRAC=0.40, _at_start excluded)
- **Mh_2026-03 production validation:** T=L=E=9, sha256 OK; исправлены 3 ошибки именования
- **FilenameGeneration Policy v_1_3 (canonical):** §4.7 byline gates; §9.1 обновлён; acceptance fixture Mh_2026-03
- **Production validated journals:** добавлен Mh (2026-03)
- **project_summary_v_2_15** → superseded by v_2_16

### v_2_15 — 2026-03-11
- **Mg_2026-02 production validation:** T=L=E=11 (1 Contents + 10 Research), sha256 OK — первый production run через Phase 3 Web UI
- **Production validated journals:** Mg (2025-12, 2026-01, 2026-02), Mh (2026-01, 2026-02), Na (2026-02)
- **project_summary_v_2_14** → superseded by v_2_15

### v_2_14 — 2026-03-11
- **Phase 3 Web UI** (MVP задеплоено 2026-03-04): добавлен milestone в §4, D8 в §8, ui/ в §6 SoT
- **Upwork portfolio assets** (2026-03-05): docs/portfolio/ в §4, §6
- **session-close-pdf_extractor** skill добавлен (зарегистрирован в project_files_index v_1_13)
- **project_files_index** обновлён до v_1_13 (doc-sync Q6)
- **Q7, Q8** зарегистрированы как открытые вопросы в §9
- **project_summary_v_2_13** → superseded by v_2_14

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
