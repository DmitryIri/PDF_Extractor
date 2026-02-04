# Project Summary — PDF Extractor

**Version:** v_2_6  
**Status:** Canonical  
**Date:** 2026-01-13

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

**Активная фаза:** Phase 1 ЗАВЕРШЕНА → Transition to Phase 2

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

### Завершённые core-компоненты
- ✅ InputValidator — реализован и принят
- ✅ PDFInspector — реализован и принят
- ✅ MetadataExtractor — реализован (v_1_0.1), извлекает anchors по всему PDF (DOI + text_block с bbox)

### В разработке
**BoundaryDetector:**
- Typography-based detection validated (Golden Test: 100% metrics)
- Detection rules формализованы:
  - PRIMARY signal: MyriadPro-BoldIt, 12pt
  - FILTER: Language-based duplicate detection (RU/EN pairs)
  - BLACKLIST: Minimal (3 items)
- Следующий шаг: Policy v_1_0 formalization + code implementation

### Блокеры
- Golden Test pending git commit (.gitignore blocking `*.json` → needs exception for `golden_tests/`)

---

## 5. Канонические документы проекта

### TechSpec
- PDF Extractor — TechSpec v_2_4 (Canonical)
- **Needs update → v_2_5:** Edition-aware architecture (билингвальная структура)

### Plan
- PDF Extractor — Plan v_2_3 (Canonical)
- **Needs update → v_2_4:** Reflect Phase 1 completion

### Policies
- ArticleStartPolicy v_1_0 (Canonical) — validated by Golden Test
- BoundaryDetector v_1_0 (Canonical)
- **Needs formalization:** ArticleStartDetection Policy v_1_0 (based on Golden Test)

### Golden Tests (NEW)
- `golden_tests/mg_2025_12_article_starts.json` (created, pending commit)

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
- `golden_tests/` — ground truth для regression testing (NEW)
- runtime-артефакты не считаются источником истины

---

## 7. Инварианты состояния

На момент v_2_6 зафиксированы следующие инварианты:

### Architectural Invariants
- MetadataExtractor не фильтрует anchors (возвращает raw observations)
- BoundaryDetector обязан строго следовать ArticleStartPolicy
- Confidence считается детерминированно
- Одиночный сигнал (например, DOI) не может быть решающим

### Validated Detection Rules (mg_2025_12)
- **PRIMARY signal:** Typography marker (MyriadPro-BoldIt, 12pt) достаточен для detection
- **FILTER required:** Language-based duplicate detection (билингвальная RU/EN структура)
- **ACCEPTANCE threshold:** Precision >= 90%, Recall >= 80% (achieved: 100%/100%)

### Edition-Specific
- Журнал "Медицинская генетика" использует билингвальную структуру:
  - RU блок (title, authors, affiliations, abstract)
  - EN блок (title, authors, affiliations, abstract) на следующей странице
- Рубрики используют отличный шрифт: MyriadPro-BoldCond, 14pt (vs MyriadPro-BoldIt, 12pt для статей)

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

---

## 9. Открытые вопросы / риски

### Риски
**R1: .gitignore blocks golden_tests (Medium)**  
**Статус:** 🟡 Блокирует commit Golden Test  
**Mitigation:** Добавить `!golden_tests/**/*.json` в .gitignore  
**Owner:** Следующая сессия (Priority 1)

### Открытые вопросы
Нет открытых вопросов на момент v_2_6.

---

## 10. Следующий шаг

**Phase 1 → Phase 2 Transition:**

### Priority 1: Завершить Golden Test commit (15 min)
- Fix .gitignore (add exception for golden_tests)
- Git commit Golden Test + .gitignore update
- **Handoff команды:** См. `session_closure_log_2026_01_13_v1_0.md`, §9

### Priority 2: ArticleStartDetection Policy v_1_0 (30 min)
- Формализовать detection rules на основе Golden Test
- Структура:
  - PRIMARY signal: Typography
  - FILTER: Language-based duplicate detection
  - ACCEPTANCE: 90% precision, 80% recall

### Priority 3: TechSpec v_2_4 → v_2_5 (1 hour)
- Edition-aware architecture
- Билингвальная структура как инвариант
- Typography marker как PRIMARY signal

### Priority 4: Plan v_2_3 → v_2_4 (30 min)
- Reflect Phase 1 completion
- Update Phase 2 scope (BoundaryDetector implementation)

**Estimated total time:** 2-3 hours

---

## 11. CHANGELOG

### v_2_6 — 2026-01-13
- **Phase 1 завершена:** Quality diagnostics + Golden Test validation
- Typography marker validated: MyriadPro-BoldIt 12pt (PRIMARY signal, 100% metrics)
- Golden Test created: mg_2025_12 (28 articles, pending commit)
- Language-based duplicate filter validated (3 EN duplicates detected)
- Transition to Phase 2: Policy formalization + BoundaryDetector implementation
- Обновлены инварианты состояния (edition-specific rules)
- Зафиксированы принятые решения (D1-D3)

### v_2_4 — 2026-01-07
- BoundaryDetector v_1_0 policy документ добавлен
- MetadataExtractor v_1_0.1: bbox для DOI-anchors
- Активная фаза: Plan v_2_3 — Шаг 2.4 BoundaryDetector
- ArticleStartPolicy v_1_0 подтверждена как canonical
