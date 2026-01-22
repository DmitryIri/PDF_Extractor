# Session Closure Log — 2026-01-21

**Проект:** PDF Extractor  
**Статус:** Canonical  
**Версия:** v_1_2  
**Scope:** Phase 2 — BoundaryDetector (stdin contract, RU/EN дедуп, golden для mg_2025_12, stdout/stderr hardening) + стабильность Claude Code/VS Code

---

## 1. Цель сессии

1) Довести Phase 2 BoundaryDetector до корректного детерминированного результата на выпуске `mg_2025_12`.
2) Зафиксировать канонический список стартовых страниц статей для `mg_2025_12` и обеспечить regression-check (golden).
3) Устранить блокирующую эксплуатационную проблему вывода BoundaryDetector (JSON должен быть в stdout, stderr — чистым).
4) Подготовить handoff для следующего чата: использовать export-файлы Claude Code как источник фактов/контекста.

---

## 2. Что было сделано (по шагам)

1) Зафиксирован вручную проверенный **канонический** список стартовых страниц статей для `mg_2025_12` (28 стартов):
   `[5, 6, 16, 28, 34, 42, 51, 67, 74, 80, 88, 97, 108, 110, 113, 116, 119, 122, 125, 130, 133, 137, 140, 143, 145, 148, 151, 154]`.
2) Исправлен **stdin-контракт** BoundaryDetector: поддержка входного envelope-формата от MetadataExtractor (unwrap `payload = raw.get("data", raw)`), устранён `exit_code=10`, возникавший из-за ожидания полей на верхнем уровне.
3) Уточнён RU/EN дедуп-алгоритм: удаляются EN-дубли стартов страниц, сохраняются RU-старты (канон подтверждён вручную).
4) Добавлен/обновлён golden-тест `golden_tests/mg_2025_12_article_starts.json` (точное равенство списка страниц).
5) Выполнен acceptance-check на `mg_2025_12`: `exit_code=0`, `Exact match: True`, `count=28`.
6) Выявлен блокер: при некоторых способах запуска в среде Claude Code успешный JSON-результат оказывался не в stdout.
7) Выполнен hardening вывода: успешный JSON принудительно пишется в stdout через `fd=1` (`os.write(1, ...)`), stderr остаётся чистым.
8) Выполнена двусторонняя верификация вывода после hardening:
   - PIPE: `cat anchors | python detector.py > out.json 2> err.log` → `out.json` валиден, `err.log` размер 0.
   - REDIRECT: `python detector.py < anchors > out.json 2> err.log` → `out.json` валиден, `err.log` размер 0.
9) Закоммичен hardening вывода:
   - Commit: `431c0a2` — `fix(boundary): harden JSON emit to stdout (fd1), keep stderr clean`.

---

## 3. Принятые решения

1) **Типографический детектор стартов статей — единственный канонический подход** для BoundaryDetector (возврат к DOI/RU-blocks подходам не рассматривается).
2) Для `mg_2025_12` канонический список стартов (28) принят как regression-oracle (golden).
3) Hardening stdout/stderr (запись JSON в stdout через fd1) — принят и зафиксирован отдельным коммитом `431c0a2`.

---

## 4. Изменения

### 4.1 Code
- `agents/boundary_detector/detector.py`
  - unwrap envelope stdin (`raw.get("data", raw)`) для совместимости с MetadataExtractor.
  - RU/EN дедуп (удаление EN-дублей стартов страниц).
  - hardening эмиттера JSON: запись в stdout через `os.write(1, ...)`, stderr должен быть чистым.

### 4.2 Tests
- `golden_tests/mg_2025_12_article_starts.json`
  - канонические 28 стартов страниц для `mg_2025_12`.

### 4.3 Артефакты handoff (не для коммита)
- `2026-01-21-task-default-mode-server.txt` — export Claude Code (Default mode).
- `2026-01-21-task-plan-mode.txt` — export Claude Code (Plan mode).

---

## 5. Проверки и критерии корректности (факты)

### 5.1 Acceptance критерии для `mg_2025_12`
- `exit_code=0`
- `count=28`
- `Exact match with golden: True`
- `stderr` пуст в режимах запуска PIPE и REDIRECT

### 5.2 Канонические команды проверки вывода (gate)
- PIPE:
  `cat /tmp/mg_2025_12_anchors.json | /srv/pdf-extractor/venv/bin/python agents/boundary_detector/detector.py > OUT.json 2> ERR.log`
- REDIRECT:
  `/srv/pdf-extractor/venv/bin/python agents/boundary_detector/detector.py < /tmp/mg_2025_12_anchors.json > OUT.json 2> ERR.log`

---

## 6. Открытые вопросы / риски

1) `.gitignore`: golden-тесты ранее требовали `git add -f`. Требуется привести к канону (golden должны быть версионируемыми без force-add).
2) Экспорт-файлы Claude Code должны быть сохранены вне git (и синхронизированы на ПК). Желательно позже определить каноническое место хранения (например, `_audit/claude_exports/`) и правило игнорирования.
3) Универсальный policy для издательства: требуется формализация RU→EN метаданных как универсального фильтра (язык + similarity заголовков), без привязки к ключевым словам.

---

## 7. Handoff — что обязательно сделать в следующем чате

### 7.1 Приоритет №1: восстановление контекста Claude Code по export-файлам
1) Найти на сервере экспортные файлы:
   - `2026-01-21-task-plan-mode.txt`
   - `2026-01-21-task-default-mode-server.txt`
2) Скопировать оба файла на локальный ПК.
3) Использовать эти экспорты как первичный источник фактов для:
   - bootstrap следующей сессии Claude Code,
   - напоминания контекста ассистенту (через загрузку в Project Files).

Рекомендуемые команды (server):
- `find /opt/projects/pdf-extractor "$HOME" -maxdepth 6 -type f -name "2026-01-21-task-*.txt" -print`

### 7.2 После восстановления контекста
- Привести репозиторий к clean state: `git status --short` должен быть пуст.
- `git push` актуальной ветки.
- Синхронизировать обновления на ПК по шпаргалке.

---

## 8. CHANGELOG

- **v_1_2** — добавлен hardening stdout/stderr (fd1 write) с верификацией PIPE/REDIRECT и фиксацией коммита `431c0a2`; уточнены артефакты handoff (два export-файла), добавлены соответствующие риски/следующие шаги.
- **v_1_1** — фиксация Phase 2 для `mg_2025_12` (канон 28 стартов, envelope unwrap, RU/EN дедуп, golden) + первичная фиксация проблемы stdout/stderr и handoff.
- **v_1_0** — исходная фиксация проблем среды и первичный план gate-прогона.

