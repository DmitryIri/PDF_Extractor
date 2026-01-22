# Project Summary — PDF Extractor

**Version:** v_2_8
**Status:** Canonical
**Date:** 2026-01-22

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

**Активная фаза:** Phase 2.5

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
- PDF Extractor — TechSpec v_2_5 (Canonical) — committed (5c4abd3)
  - Stdin envelope + stdout/stderr contract
  - Typography-based detection specification
  - Rich article_starts schema

### Plan
- PDF Extractor — Plan v_2_3 (Canonical) — updated to reference TechSpec v_2_5 (71315ff)

### Component Design Documents
- BoundaryDetector v_1_1 (Canonical) — committed (71315ff)
  - Aligned with TechSpec v_2_5
  - Typography-based PRIMARY SIGNAL (MyriadPro-BoldIt, 12.0 ± 0.5)
  - Fixed confidence=1.0 (deterministic binary match)

### Policies
- ArticleStartDetection Policy v_1_0 (Canonical) — validated by Golden Test, формализована

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

**Documentation Alignment Completed:**
- ✅ TechSpec v_2_5 committed (5c4abd3)
- ✅ Plan v_2_3 aligned to reference v_2_5 (71315ff)
- ✅ BoundaryDetector v_1_1 created and verified (71315ff)
- ✅ Audit exports infrastructure established (34344ad)

**Next Phase Decisions Required:**
- Decide push strategy for local commits (feature/phase-2-core-autonomous branch)
- Determine merge strategy (direct to main / via PR)
- Golden Test commit strategy (still pending due to .gitignore blocking `*.json`)

---

## 11. CHANGELOG

### v_2_8 — 2026-01-22
- **Documentation alignment completed:** TechSpec v_2_5, Plan v_2_3, BoundaryDetector v_1_1 all synchronized
- Audit exports infrastructure established (commit 34344ad):
  - `.claude/rules/audit_exports.md` — canonical policy for /export artifact handling
  - `.claude/skills/archive-exports/SKILL.md` — reusable archiving skill
  - `.claude/settings.json` — project-level permissions
- TechSpec v_2_5 committed (commit 5c4abd3):
  - Stdin envelope + stdout/stderr contract specification
  - Typography-based detection formalized
  - Rich article_starts output schema
- Plan v_2_3 updated to reference TechSpec v_2_5 (commit 71315ff)
- BoundaryDetector v_1_1 created (commit 71315ff):
  - Aligned with TechSpec v_2_5 and current implementation
  - Typography PRIMARY SIGNAL: MyriadPro-BoldIt, 12.0pt ± 0.5
  - Fixed confidence=1.0 (deterministic binary match)
  - Replaces probabilistic DOI/RU-blocks detection from v_1_0
- Verification evidence created in `_audit/claude_code/reports/` (not committed):
  - `verify_bd_v1_1_vs_techspec_rg.txt` — TechSpec evidence for BoundaryDetector v_1_1 claims
  - `verify_bd_v1_1_vs_code_rg.txt` — Code implementation evidence
  - `techspec_v_2_4_to_v_2_5_full.patch` — Full diff between TechSpec versions
  - SHA256 manifests for audit trail
- Status: All commits local-only (branch: feature/phase-2-core-autonomous, no push)

### v_2_7 — 2026-01-15
- Синхронизация с Plan v_2_3: активная фаза обновлена до Phase 2.5
- Унификация именования политик: "ArticleStartPolicy" → "ArticleStartDetection Policy v_1_0" (соответствие каноническому артефакту)
- Удалена неоднозначность: политика уже формализована, пометка "Needs formalization" устранена
- Дата документа синхронизирована с последним session closure log (2026-01-15)

### v_2_6 — 2026-01-15
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
