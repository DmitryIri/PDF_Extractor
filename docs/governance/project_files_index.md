# PROJECT_FILES_INDEX

**Проект:** PDF Extractor  
**Статус:** Canonical  
**Версия:** v_1_17
**Назначение:** Единая точка навигации по Project Files (Source of Truth)

---

## 1. Назначение документа

Данный документ описывает **каноническую структуру Project Files** и назначение каждого артефакта проекта PDF Extractor.

Цели документа:
- исключить путаницу между типами документов;
- обеспечить детерминированный bootstrap новых сессий и участников;
- зафиксировать, какие файлы являются **нормативными**, а какие — **состоянием проекта**;
- предоставить LLM‑first навигационный индекс для контролируемого чтения документации и запуска Claude Code.

**Важно:**  
Project Files являются **единственным Source of Truth**.  
Чаты, переписка и рабочие сессии источником истины **не являются**.

---

## 2. Классы документов (строго типизированы)

В проекте используются **четыре строго различимых класса документов**. Каждый файл относится **ровно к одному классу** и не может одновременно принадлежать нескольким классам.

---

### 🟥 A. Governance / Meta (нормативный слой)

**Назначение:** правила, политики и протоколы, определяющие способ работы над проектом.

**Свойства:**
- меняются редко;
- применяются ко всем сессиям;
- имеют приоритет при конфликтах.

**Канонические файлы:**
- `canonical_artifact_registry.md`
- `context_bootstrap_protocol.md`
- `session_closure_protocol.md`
- `session_finalization_playbook.md`
- `documentation_rules_style_guide.md`
- `versioning_policy.md`
- ~~`meta_bundle_compressed_v_1_1.md`~~ — *не канонический (отсутствует в canonical_artifact_registry.md и в репозитории)*
- `project_files_index.md`

---

### 🟧 B. Project State (As‑Is)

**Назначение:** фиксация текущего состояния проекта «как есть».

**Свойства:**
- отражают фактическую реальность;
- обновляются по результатам сессий;
- используются для восстановления контекста.

**Канонические файлы:**
- `project_summary_v_2_16.md` ← canonical
- `project_summary_v_2_15.md` ← superseded by v_2_16 (в `docs/state/`)
- `project_summary_v_2_14.md` ← superseded by v_2_15 (в `docs/state/`)
- `project_summary_v_2_13.md` ← superseded by v_2_14 (в `docs/state/`)
- `project_summary_v_2_12.md` ← superseded by v_2_13 (в `docs/state/`)
- `project_summary_v_2_11.md` ← archived → `docs/_archive/summaries/`
- `project_history_log.md`
- `context_bootstrap_2026_02_04_v_1_0.md` — bootstrap artifact (2026-02-04)
- `session_closure_log_YYYY_MM_DD_v_X_Y.md` (каждый файл — уникальная дата; naming: mixed dots/underscores — исторически; не переименовываются)
  - `session_closure_log_2026_04_01_v_1_0.md` (doc-closure: policy v_1_3, summary v_2_16)
  - `session_closure_log_2026_04_01_v_1_1.md` (CLAUDE.md + README.md rewrite; global skills claude-md-audit, readme-audit)
  - Последний: `session_closure_log_2026_04_01_v_1_1.md`
- `execution_report_2026_02_04_universal_surname_selection_fix.md`

---

### 🟨 C. Project Design (To‑Be)

**Назначение:** описание целевой архитектуры и плана реализации.

**Свойства:**
- определяют, как *должно быть*;
- меняются осознанно и версионируются;
- не обязаны совпадать с текущим состоянием.

**Канонические файлы (текущие версии):**
- `pdf_extractor_techspec_v_2_8.md` ← canonical
- `pdf_extractor_plan_v_2_5.md` ← canonical
- `pdf_extractor_boundary_detector_v_1_3.md` ← canonical

**Superseded (не архивированы, immutable):**
- `pdf_extractor_techspec_v_2_7.md` ← superseded by v_2_8 (в `docs/design/`)
- `pdf_extractor_techspec_v_2_6.md` ← superseded by v_2_7 (в `docs/design/`)
- `pdf_extractor_plan_v_2_4.md` ← superseded by v_2_5 (в `docs/design/`)
- `pdf_extractor_boundary_detector_v_1_2.md` ← superseded by v_1_3 (в `docs/design/`)
- (v_2_5 и ранее — в `_archive/techspec/`; v_1_1 и ранее — в `_archive/design/`)

> **Примечание:** Имена файлов Design-артефактов нормализованы к формату `v_X_Y` (underscore-разделители) в рамках репозитория (2026-01-15).

---

### 🟦 E. Policy Documents

**Назначение:** версионированные политики принятия решений в pipeline.

**Свойства:**
- определяют детерминированные правила обработки;
- версионируются при любых изменениях;
- являются нормативными для соответствующих компонентов.

**Канонические файлы (текущие версии):**
- `article_start_detection_policy_v_1_0.md` ← canonical (legacy alias `article_start_policy_v_1_0.md` в `_archive/policies/`)
- `filename_generation_policy_v_1_3.md` ← canonical
- `filename_generation_policy_v_1_2.md` ← superseded by v_1_3 (immutable)

---

### 🟩 D. Infrastructure State (As‑Is)

**Назначение:** фиксация состояния среды выполнения и инфраструктуры.

**Свойства:**
- обновляются только при реальных изменениях инфраструктуры;
- критичны для DR и восстановления;
- не содержат проектных решений.

**Статус:** Out of scope / deferred для данного репозитория.

> **Примечание:** Директория `docs/infrastructure/` и артефакт `server_latvia_summary_v_X_Y.md` в данном репозитории не поддерживаются. Для их добавления требуется расширение canonical_artifact_registry.md.

---

## 3. Правила работы с Project Files

1. **Один файл — одна роль.** Документ не может одновременно быть governance и state.
2. **Имя файла является частью контракта.** Неверное имя означает, что документ некорректен.
3. **Project Files содержат только актуальное состояние.** Старые версии не должны конкурировать с текущими.
4. **Любые изменения фиксируются осознанно.** Обновление сопровождается увеличением версии и, при необходимости, Session Closure Log.

---

## 4. Минимальный bootstrap новой сессии

Для корректного начала новой сессии **обязателен** следующий минимальный пакет:

1. `project_summary_v_X_Y.md`
2. последний `session_closure_log_YYYY_MM_DD_v_X_Y.md`
3. `project_history_log.md`

При необходимости дополнительно подключаются:
- TechSpec / Plan — при обсуждении архитектуры и реализации;
- Server Summary — при затрагивании инфраструктуры.

---

## 5. Физические пути в репозитории (канон)

Единый канонический корень проекта:

`/opt/projects/pdf-extractor`

Структура Project Files:

- `docs/governance/`
  - `canonical_artifact_registry.md`
  - `context_bootstrap_protocol.md`
  - `session_closure_protocol.md`
  - `session_finalization_playbook.md`
  - `documentation_rules_style_guide.md`
  - `versioning_policy.md`
  - ~~`meta_bundle_compressed_v_1_1.md`~~ — *не канонический*
  - `project_files_index.md`

- `docs/state/`
  - `project_summary_v_X_Y.md`
  - `project_history_log.md`
  - `session_closure_log_YYYY_MM_DD_v_X_Y.md`

- `docs/design/`
  - `pdf_extractor_techspec_v_2_8.md` (canonical)
  - `pdf_extractor_plan_v_2_5.md` (canonical)
  - `pdf_extractor_boundary_detector_v_1_3.md` (canonical)

- `docs/governance/task_specs/`
  - `task_spec_phase_3_ui_db_bootstrap_v_1_0.md`
  - `run_pipeline_design_v_1_0.md` — Design spec для `/run-pipeline` skill

- `docs/policies/`
  - `article_start_detection_policy_v_1_0.md` (canonical)
  - `filename_generation_policy_v_1_0.md` (immutable, superseded by v_1_1)
  - `filename_generation_policy_v_1_1.md` (immutable, superseded by v_1_2)
  - `filename_generation_policy_v_1_3.md` (canonical)
  - `filename_generation_policy_v_1_2.md` (immutable, superseded by v_1_3)

- `.claude/agents/`
  - `doc-agent.md` — Doc-Agent: single authorized writer for docs/**

- `.claude/skills/`
  - `doc-create/SKILL.md` — создание новых версионированных документов
  - `doc-review/SKILL.md` — read-only проверки документации
  - `doc-update/SKILL.md` — version bump существующих документов
  - `doc-index/SKILL.md` — синхронизация project_files_index
  - `session-init-pdf_extractor/SKILL.md` — project-specific session kickoff (без /srv/* paths)
  - `session-close-pdf_extractor/SKILL.md` — session closure workflow для pdf-extractor

- `.claude/rules/`
  - `single_writer_contract_v_1_0.md` — единственный writer для docs/**

- `ui/`
  - `main.py` — FastAPI application entry point (Phase 3 Web UI)
  - `db.py` — SQLite database layer (runs.db)
  - `pipeline.py` — asyncio subprocess pipeline runner
  - `templates/` — Jinja2 HTML templates (base, index, run, history)

- `docs/portfolio/`
  - `architecture.md` — ASCII pipeline diagram + production validation table (Upwork portfolio)
  - `screenshots_plan.md` — guide: 3 скрина для Upwork
  - `upwork_project_1_description.md` — текст проекта для Upwork (~550 символов)

- `docs/_archive/`
  - See `docs/_archive/legacy_aliases/2026_02_04/README.md` for full move manifest

- `docs/infrastructure/` — *не поддерживается в данном репозитории (см. §2.D)*

---

## 6. Claude Code Bootstrap (обязательный сценарий)

Данный раздел определяет **единственный допустимый сценарий начала работы в Claude Code**.

### 6.1 Минимальный набор файлов для чтения Claude

Claude Code **обязан** прочитать и интерпретировать документы строго в следующем порядке:

1. `docs/governance/project_files_index.md`
2. `docs/state/project_summary_v_X_Y.md`
3. `docs/state/session_closure_log_YYYY_MM_DD_v_X_Y.md` (последний)
4. `docs/state/project_history_log.md`

Без чтения этих файлов Claude **запрещено**:
- выполнять `/init`;
- предлагать архитектурные или кодовые изменения;
- делать выводы о состоянии проекта.

### 6.2 Генерация `claude.md`

Файл `claude.md` может быть создан **только после**:
- подтверждения корректности Project Files Index;
- отсутствия противоречий между State‑артефактами.

`claude.md` является производным артефактом и **не входит** в Project Files.

### 6.3 Запуск `/init`

Команда `/init` в Claude Code допускается **исключительно после**:
- чтения файлов из п.6.1;
- генерации и проверки `claude.md`.

Любое отклонение от данного сценария считается нарушением governance.

---

## 7. CHANGELOG

- **v_1_17 — 2026-04-01** — session_closure_log_2026_04_01_v_1_1 добавлен (CLAUDE.md rewrite 460→177 строк; README.md rewrite 63→100 строк; global skills claude-md-audit, readme-audit); последний closure log обновлён в §2.B.
- **v_1_16 — 2026-04-01** — filename_generation_policy v_1_2 → v_1_3 (canonical, RU single-initial byline fix); project_summary v_2_15 → v_2_16 (Mh_2026-03 validation, MetadataExtractor v1.3.3).
- **v_1_15 — 2026-03-31** — session_closure_log_2026_03_31_v_1_0 добавлен (Mh_2026-03: running-header exclusion + single-initial support); последний closure log обновлён в §2.B.
- **v_1_14 — 2026-03-11** — project_summary v_2_14 → v_2_15 (Mg_2026-02 production validation via Web UI).
- **v_1_13 — 2026-03-11** — Doc-sync Q6: добавлены `session-close-pdf_extractor/SKILL.md` (в .claude/skills/), `ui/` (Phase 3 Web UI), `docs/portfolio/` (Upwork assets). Последний closure log → session_closure_log_2026_03_05_v_1_1.md.
- **v_1_12 — 2026-03-04** — session_closure_log_2026_03_04_v_1_2 добавлен (Phase 3 UI MVP); последний closure log обновлён в §2.B.
- **v_1_11 — 2026-03-04** — RFC-4: TechSpec v_2_7 → v_2_8 (canonical); добавлен §6.4 inbox/ как canonical input path с политикой хранения/очистки.
- **v_1_10 — 2026-03-04** — Doc sync сессии 2026-03-04: project_summary v_2_12→v_2_13 (canonical), v_2_11 archived; plan v_2_4→v_2_5 (canonical, добавлен info material_kind); session-init-pdf_extractor skill добавлен в .claude/skills/. Физические пути обновлены.
- **v_1_9 — 2026-02-21** — Doc-agent инфраструктура: добавлены .claude/agents/doc-agent.md, .claude/rules/single_writer_contract_v_1_0.md, .claude/skills/doc-*/SKILL.md. Design docs bump: techspec v_2_7, boundary_detector v_1_3. Policy bump: filename_generation_policy v_1_2 (info material_kind). State update: project_summary → v_2_12, session_closure_log_2026_02_21 добавлен.
- **v_1_8 — 2026-02-04** — Docs canonicalization: все семейства приведены к единому entry point. Архивированы superseded design docs (techspec v_2_5, boundary_detector v_1_1), old summaries (v_2_6–v_2_10), working artifact REPORT. Удалён pre-sync duplicate session_closure_log. Added explicit canonical pointers + archive notes in §2, §5. Зарегистрирован task_specs/ в §5.
- **v_1_7 — 2026-02-04** — Зарегистрирован `filename_generation_policy_v_X_Y.md` в §2.E и §5 (filename generation policy v_1_0 + v_1_1).
- **v_1_6 — 2026-01-20** — Миграция к формату версий v_X_Y: обновлены шаблоны и ссылки согласно versioning_policy v_2_0.
- **v_1_5 — 2026‑01‑15** — Добавлен класс Policy Documents (§2.E) и каноническая директория `docs/policies/`. Зарегистрирован `article_start_detection_policy_v_1_0.md`.
- **v_1_4 — 2026‑01‑15** — Устранение противоречий: (a) имена TechSpec/Plan заменены на фактические файлы репозитория; (b) `meta_bundle_compressed_v_1_1.md` реклассифицирован как не канонический (отсутствует в реестре и репозитории); (c) статус `docs/infrastructure/` уточнён как «out of scope / deferred» для данного репозитория.
- **v_1_3 — 2026‑01‑14** — Полное пересоздание документа как Claude‑ready канонического Canvas‑артефакта: добавлены физические пути в репозитории и обязательный сценарий Claude Code Bootstrap. Требования и роли документов не изменены.
- **v_1_2 — 2026‑01‑14** — Нормализация структуры документа и устранение неоднозначностей без изменения правил.
- **v_1_1 — 2026‑01‑13** — Первичная каноническая фиксация структуры Project Files.

