# Session Closure Log

**Дата:** 2026-03-04
**Версия:** v_1_2
**Ветка:** main
**HEAD:** 19702a6 (до коммита этой сессии)
**Scope:** /opt/projects/pdf-extractor

---

## 1. Meta

| Параметр | Значение |
|---|---|
| Дата | 2026-03-04 |
| Ветка | main |
| HEAD до коммита | 19702a6 |
| Scope | /opt/projects/pdf-extractor |
| Предыдущий лог | session_closure_log_2026_03_04_v_1_1.md |

---

## 2. Цель сессии

Phase 3 UI — разработка и деплой веб-интерфейса для pdf-extractor:
- Страница загрузки PDF выпуска журнала
- Запуск pipeline и отображение прогресса
- Скачивание результата ZIP-архивом (articles + manifest + checksums + README)
- Безопасный доступ через SSH tunnel (127.0.0.1:8080)

---

## 3. Что было сделано (по шагам)

### 3.1 Планирование (Plan Mode)
- Изучена task_spec_phase_3_ui_db_bootstrap_v_1_0.md
- Исследован pipeline CLI (run_issue_pipeline.sh, exit codes, output структура)
- Исследовано состояние runtime venv (нет веб-фреймворков)
- Изучены Anthropic skills: frontend-design (design principles), web-artifacts-builder (Tailwind pattern)
- Resolvedы все 5 Decision Points (D-P3-1 → D-P3-5):
  - D-P3-1: SQLite (local, /srv/pdf-extractor/db/runs.db)
  - D-P3-2: SSH tunnel + bind 127.0.0.1 (нет auth-кода)
  - D-P3-3: Local filesystem (текущий export layout)
  - D-P3-4: FastAPI + Tailwind CSS CDN + HTMX CDN
  - D-P3-5: asyncio.create_subprocess_exec + asyncio.create_task

### 3.2 Реализация ui/ (новый пакет)

Созданы файлы:

| Файл | Назначение |
|---|---|
| `ui/__init__.py` | Пакет |
| `ui/db.py` | SQLite: schema, create_run, get_run, get_active_run, update_run, fail_orphaned_runs |
| `ui/pipeline.py` | asyncio subprocess wrapper, parse_issue_id, expected_filename_prefix, build_zip |
| `ui/main.py` | FastAPI: 6 маршрутов, валидации, size limit 300 MB, single-flight guard |
| `ui/templates/base.html` | IBM Plex Sans + Tailwind CDN + HTMX CDN |
| `ui/templates/index.html` | Upload form: drag&drop, journal+issue fields, filename hint |
| `ui/templates/run.html` | Страница статуса запуска |
| `ui/templates/partials/status_card.html` | HTMX polling card (pending/running/done/failed) |
| `ui/templates/history.html` | История последних 20 запусков |

### 3.3 Ключевые реализованные инварианты
- **Single-flight**: при активном run новый запуск запрещён (redirect на текущий run)
- **Filename validation**: `expected_filename_prefix(journal_code, issue_id)` → `Mg_2025-12`; имя файла обязано начинаться с этого префикса
- **Size limit**: 300 MB, чтение чанками (64 KB), partial file cleanup при превышении
- **Orphan cleanup**: при рестарте сервиса pending/running runs → failed
- **ZIP structure**: articles/ + manifest/export_manifest.json + checksums.sha256 + README.md (sha256sum-compatible)
- **Timeout**: 6 часов, после — SIGKILL

### 3.4 Установка зависимостей
```
/srv/pdf-extractor/venv/bin/pip install fastapi uvicorn jinja2 aiofiles python-multipart
```
Установлено: fastapi-0.135.1, uvicorn-0.41.0, jinja2-3.1.6, aiofiles-25.1.0, python-multipart-0.0.22

### 3.5 Деплой systemd
- Создан `/etc/systemd/system/pdf-extractor-ui.service`
- `systemctl enable --now pdf-extractor-ui` — активен
- Bind: 127.0.0.1:8080 (проверено: `ss -lntp | grep 8080`)

### 3.6 Smoke test (пройден)
- HTTP 200: GET /, GET /history
- HTTP 404: GET /runs/nonexistent
- HTTP 422: POST /upload (без тела)
- 127.0.0.1:8080 — только localhost
- SSH tunnel: `ssh -L 18080:localhost:8080 dmitry@2.58.98.101` → http://localhost:18080 → ✅ работает

---

## 4. Изменения

### Code (незакоммичено — требует коммита)

| Файл | Статус |
|---|---|
| `ui/__init__.py` | Новый |
| `ui/db.py` | Новый |
| `ui/pipeline.py` | Новый |
| `ui/main.py` | Новый |
| `ui/templates/base.html` | Новый |
| `ui/templates/index.html` | Новый |
| `ui/templates/run.html` | Новый |
| `ui/templates/partials/status_card.html` | Новый |
| `ui/templates/history.html` | Новый |
| `.gitignore` | Изменён (добавлен `ui/__pycache__/`) |

### Server (runtime, не SoT)
- `/etc/systemd/system/pdf-extractor-ui.service` — создан, enabled, running
- `/srv/pdf-extractor/db/` — создан (SQLite DB dir)
- `/srv/pdf-extractor/logs/ui_runs/` — создан
- `/srv/pdf-extractor/venv/` — установлены fastapi, uvicorn, jinja2, aiofiles, python-multipart

### Docs
- Нет изменений в docs/** (требуется doc-sync — см. §7)

---

## 5. Принятые решения

| Decision | Выбор | Обоснование |
|---|---|---|
| DB backend | SQLite | Single-user, нет внешних зависимостей |
| Auth | SSH tunnel + 127.0.0.1 | Максимальная безопасность, нуль auth-кода |
| Storage | Local filesystem | Pipeline уже пишет в /srv/pdf-extractor/exports/ |
| UI framework | FastAPI + Tailwind CDN + HTMX CDN | Python-only, нет Node.js/сборки |
| Pipeline invocation | asyncio.create_subprocess_exec + create_task | Non-blocking, fits FastAPI event loop |
| ZIP содержимое | articles/ + manifest/ + checksums.sha256 + README.md | DR-пакет: sha256sum-verifiable |
| Filename validation | prefix match: `{JournalCode}_{YYYY}-{MM}` | Детерминированное правило из issue_id |
| SSH tunnel port | 18080 (локальный PC) | 8080 и 8081 были заняты на PC |

---

## 6. Риски / проблемы

- Нет активных рисков
- При рестарте сервиса: orphaned runs → failed (реализовано, acceptable для MVP)

---

## 7. Открытые вопросы

- **Q1:** Golden test для Mh_2026-02 — не создан
- **Q2:** MetadataExtractor выбирает рубрику вместо ru_title (журнал Mh) — отложено
- **RFC-5:** Задокументировать или удалить `repo-health` skill
- **Doc-sync pending:** созданы `ui/**` (новый пакет). Docs to update:
  - `docs/governance/project_files_index.md`: добавить ui/ директорию
  - `docs/state/project_summary`: создать v_2_14 (Phase 3 started, UI MVP deployed)
  - `docs/design/pdf_extractor_plan_v_2_5.md` или новый plan: добавить Phase 3 progress
- **UI: следующие сессии**:
  - AC1–AC7: полное acceptance testing с реальным PDF
  - Error UX polish (детальные сообщения об ошибках pipeline по шагам)
  - Журналы: расширить список known journals (добавить новые по мере появления)

---

## 8. Точка остановки

**Где остановились:** ui/ создан, сервис запущен, smoke-test пройден, доступ через SSH tunnel подтверждён (http://localhost:18080 работает). Коммит ещё не сделан.

**Следующий шаг:**
1. Закоммитить ui/ + .gitignore: `feat(ui): Phase 3 MVP — FastAPI UI`
2. Doc-sync: обновить project_files_index + project_summary v_2_14
3. AC1–AC7: полное end-to-end тестирование с реальным PDF

**Блокеры:** нет

---

## 9. Ссылки на актуальные документы

- TechSpec: `docs/design/pdf_extractor_techspec_v_2_8.md`
- Plan: `docs/design/pdf_extractor_plan_v_2_5.md`
- Project Summary: `docs/state/project_summary_v_2_13.md`
- Phase 3 bootstrap: `docs/governance/task_specs/task_spec_phase_3_ui_db_bootstrap_v_1_0.md`
- Project Files Index: `docs/governance/project_files_index.md` (v_1_11)

---

## 10. CHANGELOG

### v_1_2 — 2026-03-04
- Closure log для сессии Phase 3 UI MVP
- Реализован и задеплоен FastAPI UI (ui/ пакет)
- Smoke-test пройден, доступ подтверждён
