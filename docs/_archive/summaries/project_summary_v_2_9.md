# Project Summary — PDF Extractor

**Version:** v_2_9
**Status:** Canonical
**Date:** 2026-01-26

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
8. OutputValidator

Каждый компонент:
- изолирован;
- не знает о n8n;
- принимает JSON через stdin;
- возвращает JSON через stdout;
- завершает работу детерминированным exit-code.

---

## 4. Текущее состояние реализации (As-Is)

**Активная фаза:** Phase 2.7 (OutputBuilder)

### Завершённые milestones

#### Phase 0: Infrastructure
- ✅ Python venv setup
- ✅ Runtime/code separation (`/opt/projects/` vs `/srv/`)

#### Phase 1: Quality Diagnostics + Golden Test
- ✅ Anchors quality diagnostics (ru_* noise analysis completed)
- ✅ Typography extraction capability validated (MyriadPro-BoldIt 12pt)
- ✅ Golden Test created and validated:
  - Issue: mg_2025_12
  - Total articles: 28
  - Precision: 100%
  - Recall: 100%
  - F1-score: 100%

#### Phase 2: Core Pipeline Components

### Завершённые core-компоненты
- ✅ InputValidator — реализован и принят
- ✅ PDFInspector — реализован и принят
- ✅ MetadataExtractor — реализован (v_1_0.1), извлекает anchors по всему PDF (DOI + text_block с bbox)
- ✅ BoundaryDetector — реализован (v_1_1), детерминированное определение границ статей по typography
- ✅ Splitter — реализован (коммит 3bbf4a1, 2026-01-23), физическая разрезка PDF по boundary_ranges
- ✅ MetadataVerifier — реализован (коммит 6d67412, 2026-01-23), верификация и обогащение manifest
- ✅ OutputBuilder — реализован (2026-01-26), экспорт статей на FS с canonical naming

### В разработке
**OutputValidator:**
- Следующий компонент для реализации
- Финальная валидация: T = L = E инвариант, checksums, naming rules

### Блокеры
Нет активных блокеров.

---

## 5. Канонические документы проекта

### TechSpec
- PDF Extractor — TechSpec v_2_5 (Canonical) — committed (5c4abd3)
  - Stdin envelope + stdout/stderr contract
  - Typography-based detection specification
  - Rich article_starts schema

### Plan
- PDF Extractor — Plan v_2_4 (Canonical) — acceptance: confidence == 1.0 (binary match), rich `article_starts` objects; supersedes v_2_3

### Component Design Documents
- BoundaryDetector v_1_1 (Canonical) — committed (71315ff)
  - Aligned with TechSpec v_2_5
  - Typography-based PRIMARY SIGNAL (MyriadPro-BoldIt, 12.0 ± 0.5)
  - Fixed confidence=1.0 (deterministic binary match)

### Policies
- ArticleStartDetection Policy v_1_0 (Canonical) — validated by Golden Test, формализована

### Golden Tests
- `golden_tests/mg_2025_12_article_starts.json` — committed (2026-01-23)
- `golden_tests/mg_2025_12_anchors.json` — committed (2026-01-23)
- `golden_tests/mg_2025_12_boundaries.json` — committed (2026-01-23)
- `golden_tests/mg_2025_12_splitter_output.json` — committed (2026-01-23)

### Governance / Meta
- canonical_artifact_registry.md
- context_bootstrap_protocol.md
- session_closure_protocol.md
- session_finalization_playbook.md
- documentation_rules_style_guide.md
- versioning_policy.md

---

## 6. Source of Truth

**Единый источник истины:** Git-репозиторий
`/opt/projects/pdf-extractor`

- `agents/` — код core-компонентов
- `docs/` — TechSpec, Plan, policies, summaries
- `golden_tests/` — ground truth для regression testing
- `tests/` — unit и integration тесты
- runtime-артефакты не считаются источником истины

---

## 7. Инварианты состояния

### Architectural Invariants
- MetadataExtractor не фильтрует anchors (возвращает raw observations)
- BoundaryDetector обязан строго следовать ArticleStartPolicy
- Confidence считается детерминированно
- Одиночный сигнал (например, DOI) не может быть решающим
- T = L = E инвариант: количество статей в JSON = количество имен файлов = количество реальных PDF

### Validated Detection Rules (mg_2025_12)
- **PRIMARY signal:** Typography marker (MyriadPro-BoldIt, 12pt) достаточен для detection
- **FILTER required:** Language-based duplicate detection (билингвальная RU/EN структура)
- **ACCEPTANCE threshold:** Precision >= 90%, Recall >= 80% (achieved: 100%/100%)

### Edition-Specific
- Журнал "Медицинская генетика" использует билингвальную структуру:
  - RU блок (title, authors, affiliations, abstract)
  - EN блок (title, authors, affiliations, abstract) на следующей странице
- Рубрики используют отличный шрифт: MyriadPro-BoldCond, 14pt (vs MyriadPro-BoldIt, 12pt для статей)

### Export Structure Invariants (NEW)
- Экспортная иерархия: `/srv/pdf-extractor/exports/{JournalCode}/{YYYY}/{IssuePrefix}/exports/{export_id}/`
- Atomic export: сборка в `{export_id}.tmp/` → atomic rename в `{export_id}/`
- Naming rule: `{IssuePrefix}_{PPP-PPP}_{FirstAuthorSurname}.pdf` (PPP = 3-digit zero-padded page numbers)
- Обязательные файлы в export package: `articles/`, `manifest/export_manifest.json`, `checksums.sha256`, `README.md`

---

## 8. Принятые решения

### D1: Typography Marker as PRIMARY Signal (2026-01-13)
**Решение:** MyriadPro-BoldIt, 12pt достаточен как PRIMARY signal для article start detection.
**Обоснование:** Golden Test mg_2025_12: Precision 100%, Recall 100%.
**Ссылка:** `session_closure_log_2026_01_13_v1_0.md`, §5.

### D2: Language-Based Duplicate Filter (2026-01-13)
**Решение:** Применять proximity filter с language detection для фильтрации EN-дубликатов.
**Обоснование:** Билингвальная структура журнала (RU + EN на соседних страницах).
**Ссылка:** `session_closure_log_2026_01_13_v1_0.md`, §5.

### D3: Golden Test as Canonical Ground Truth (2026-01-13)
**Решение:** `mg_2025_12_article_starts.json` является canonical reference для regression testing.
**Обоснование:** 100% validated by domain expert, детерминированный baseline.
**Ссылка:** `golden_tests/mg_2025_12_article_starts.json`

### D4: Canonical Export Structure (2026-01-23)
**Решение:** FS-only export structure без DB/UI.
**Структура:** `/srv/pdf-extractor/exports/{JournalCode}/{YYYY}/{IssuePrefix}/exports/{export_id}/`
**Обоснование:** Deterministic, auditable, filesystem-based export для максимальной прозрачности.
**Ссылка:** `session_closure_log_2026_01_23_v_1_2.md`, §3.3.

---

## 9. Открытые вопросы / риски

### Открытые вопросы
**Q1: Источник first_author_surname**
**Статус:** 🟡 Известное ограничение
**Описание:** Между Splitter и MetadataVerifier необходим промежуточный компонент (или модификация Splitter) для извлечения `first_author_surname` из anchors или PDF.
**Workaround:** MetadataVerifier принимает `first_author_surname` во входных данных; для полного pipeline требуется upstream обогащение.
**Owner:** Future phase (после OutputValidator)

**Q2: Политика повторных экспортов**
**Статус:** 🟡 Не реализовано
**Описание:** Как инкрементировать `export_id` при повторных экспортах одного и того же issue.
**Варианты:** временная метка (текущая реализация), счётчик версий (`__export_v1`, `__export_v2`), или комбинация.
**Owner:** Future enhancement

### Риски
Нет активных рисков.

---

## 10. Следующий шаг

**Phase 2.7 OutputBuilder — Завершён:**
- ✅ OutputBuilder реализован и протестирован
- ✅ Интеграционный тест MetadataVerifier → OutputBuilder успешен
- ✅ Export structure валидирована (checksums OK)

**Next Phase:**
- **Phase 2.8 OutputValidator** (Plan v_2_4 §5.9, Шаг 2.8)
  - Финальная валидация T = L = E инварианта
  - Проверка naming rules и file integrity
  - Финальный статус `success` для всего pipeline

---

## 11. CHANGELOG

### v_2_9 — 2026-01-26
- **Phase 2.7 OutputBuilder завершён:**
  - Реализован компонент `agents/output_builder/builder.py`
  - Stdin/stdout envelope contract per TechSpec v_2_5
  - Atomic export: сборка в `.tmp/` → atomic rename
  - Export structure: `/srv/pdf-extractor/exports/{JournalCode}/{YYYY}/{IssuePrefix}/exports/{export_id}/`
  - Обязательные артефакты: `articles/`, `manifest/export_manifest.json`, `checksums.sha256`, `README.md`
  - Naming rule: `{IssuePrefix}_{PPP-PPP}_{FirstAuthorSurname}.pdf` (3-digit zero-padded pages)
  - Exit codes: 0=success, 10=invalid_input, 40=build_failed, 50=internal_error
- **Тестирование:**
  - Добавлены unit tests: `tests/test_output_builder.sh` (5 тестов: happy path + 4 negative)
  - Интеграционный тест MetadataVerifier → OutputBuilder успешен (3 статьи экспортированы корректно)
  - Checksums валидированы: все статьи OK
- **Fixtures:**
  - Добавлен `tests/fixtures/output_builder_input_minimal.json`
- **Документация:**
  - Обновлён Project Summary v_2_8 → v_2_9
  - Зафиксирован decision D4 (Canonical Export Structure)
  - Задокументировано ограничение Q1 (источник first_author_surname)
- **Активная фаза:** Phase 2.7 → Phase 2.8 (OutputValidator)
- **Статус:** All commits local-only (branch: feature/phase-2-core-autonomous), push не выполнялся

### v_2_8 — 2026-01-22
- **Documentation alignment completed:** TechSpec v_2_5, Plan v_2_3, BoundaryDetector v_1_1 all synchronized (Note: Canonical Plan is now v_2_4 to align acceptance invariants)
- Audit exports infrastructure established (commit 34344ad)
- TechSpec v_2_5 committed (commit 5c4abd3)
- Plan v_2_3 updated to reference TechSpec v_2_5 (commit 71315ff)
- BoundaryDetector v_1_1 created (commit 71315ff)
- Status: All commits local-only (branch: feature/phase-2-core-autonomous, no push)

### v_2_7 — 2026-01-15
- Синхронизация с Plan v_2_4: активная фаза обновлена до Phase 2.5
- Унификация именования политик: "ArticleStartPolicy" → "ArticleStartDetection Policy v_1_0"
- Дата документа синхронизирована с последним session closure log (2026-01-15)

### v_2_6 — 2026-01-15
- **Phase 1 завершена:** Quality diagnostics + Golden Test validation
- Typography marker validated: MyriadPro-BoldIt 12pt (PRIMARY signal, 100% metrics)
- Golden Test created: mg_2025_12 (28 articles)
- Language-based duplicate filter validated (3 EN duplicates detected)
- Transition to Phase 2: Policy formalization + BoundaryDetector implementation

