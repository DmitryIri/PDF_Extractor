# PROJECT_FILES_INDEX

**Проект:** PDF Extractor  
**Статус:** Canonical  
**Версия:** v_1_7  
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
- `project_summary_v_X_Y.md`
- `project_history_log.md`
- `session_closure_log_YYYY_MM_DD_v_X_Y.md`

---

### 🟨 C. Project Design (To‑Be)

**Назначение:** описание целевой архитектуры и плана реализации.

**Свойства:**
- определяют, как *должно быть*;
- меняются осознанно и версионируются;
- не обязаны совпадать с текущим состоянием.

**Канонические файлы:**
- `pdf_extractor_techspec_v_X_Y.md`
- `pdf_extractor_plan_v_X_Y.md`
- `pdf_extractor_boundary_detector_v_X_Y.md`

> **Примечание:** Имена файлов Design-артефактов нормализованы к формату `v_X_Y` (underscore-разделители) в рамках репозитория (2026-01-15).

---

### 🟦 E. Policy Documents

**Назначение:** версионированные политики принятия решений в pipeline.

**Свойства:**
- определяют детерминированные правила обработки;
- версионируются при любых изменениях;
- являются нормативными для соответствующих компонентов.

**Канонические файлы:**
- `article_start_detection_policy_v_X_Y.md`
- `filename_generation_policy_v_X_Y.md`

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
  - `pdf_extractor_techspec_v_X_Y.md`
  - `pdf_extractor_plan_v_X_Y.md`
  - `pdf_extractor_boundary_detector_v_X_Y.md`

- `docs/policies/`
  - `article_start_detection_policy_v_1_0.md`
  - `filename_generation_policy_v_1_0.md`
  - `filename_generation_policy_v_1_1.md`

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

- **v_1_7 — 2026-02-04** — Зарегистрирован `filename_generation_policy_v_X_Y.md` в §2.E и §5 (filename generation policy v_1_0 + v_1_1).
- **v_1_6 — 2026-01-20** — Миграция к формату версий v_X_Y: обновлены шаблоны и ссылки согласно versioning_policy v_2_0.
- **v_1_5 — 2026‑01‑15** — Добавлен класс Policy Documents (§2.E) и каноническая директория `docs/policies/`. Зарегистрирован `article_start_detection_policy_v_1_0.md`.
- **v_1_4 — 2026‑01‑15** — Устранение противоречий: (a) имена TechSpec/Plan заменены на фактические файлы репозитория; (b) `meta_bundle_compressed_v_1_1.md` реклассифицирован как не канонический (отсутствует в реестре и репозитории); (c) статус `docs/infrastructure/` уточнён как «out of scope / deferred» для данного репозитория.
- **v_1_3 — 2026‑01‑14** — Полное пересоздание документа как Claude‑ready канонического Canvas‑артефакта: добавлены физические пути в репозитории и обязательный сценарий Claude Code Bootstrap. Требования и роли документов не изменены.
- **v_1_2 — 2026‑01‑14** — Нормализация структуры документа и устранение неоднозначностей без изменения правил.
- **v_1_1 — 2026‑01‑13** — Первичная каноническая фиксация структуры Project Files.

