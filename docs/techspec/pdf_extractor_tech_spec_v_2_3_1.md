# PDF Extractor — TechSpec v2.3.1

**Статус:** Canonical (Self‑Contained)
**Дата:** 2025‑12‑28
**Предыдущая версия:** TechSpec v2.3

---

## 1. Назначение документа

Данный документ является **единственным и самодостаточным техническим заданием (TechSpec)** для реализации проекта **PDF Extractor**.

Документ:
- не требует обращения к предыдущим версиям;
- содержит полное описание архитектуры, инвариантов, пайплайна и контрактов;
- предназначен для прямой передачи разработчику как каноническое ТЗ.

---

## 2. Архитектурные инварианты (NON‑NEGOTIABLE)

1. **Python‑only.** Вся вычислительная, проверочная и трансформационная логика реализуется исключительно на Python.
2. **n8n — только оркестратор.** Любая бизнес‑логика, проверки или ветвления в n8n запрещены.
3. **LLM отсутствует в runtime.** Использование LLM допускается только на этапе проектирования.
4. **Детерминизм.** Одинаковый вход → одинаковый выход.
5. **Явные ошибки.** Любая ошибка выражается комбинацией `exit code` + структурированный JSON.
6. **Инвариант T = L = E (консистентность артефактов).**
   - **T** — количество статей в итоговом JSON;
   - **L** — количество имён файлов;
   - **E** — количество реально созданных PDF.
   Нарушение инварианта → `exit code 30 (verification_failed)`.
7. **Code ≠ Runtime.** Код и runtime‑артефакты физически и логически разделены.

---

## 3. Роль инструментов

- **Python:** реализация всех core‑компонентов пайплайна.
- **n8n:** линейная оркестрация вызовов Python‑команд и сбор статусов.
- **Storage (Supabase / FS):** хранение исходных PDF и итоговых артефактов.

---

## 4. Pipeline Flow (каноническая последовательность)

Компоненты выполняются **строго последовательно**:

1. InputValidator
2. PDFInspector
3. MetadataExtractor (FULL PDF)
4. BoundaryDetector
5. Splitter
6. MetadataVerifier
7. OutputBuilder
8. OutputValidator

### Правило остановки

При любом `exit code ≠ 0`:
- пайплайн немедленно останавливается;
- последующие компоненты не запускаются;
- n8n возвращает финальный статус `failed`.

---

## 5. Inter‑component Communication

**Вход:** JSON через `stdin`

**Выход:** JSON через `stdout`

**Логи:** `stderr`

**Бинарные данные:** ссылки на storage (Supabase / FS)

### Единый формат ответа
```json
{
  "status": "success" | "error",
  "component": "ComponentName",
  "version": "x.y.z",
  "data": { },
  "error": { }
}
```

---

## 6. Project File System Layout (Code ≠ Runtime)

### 6.1. Code — Source of Truth

`/opt/projects/pdf-extractor/`

- `agents/` — Python core‑компоненты пайплайна
- `tests/` — unit и golden‑тесты
- `docs/` — TechSpec, Plan, архитектурная документация

Код хранится в Git и является **единственным источником истины**.

### 6.2. Runtime — НЕ Source of Truth

`/srv/pdf-extractor/`

- `venv/` — виртуальное окружение Python
- `runs/<run_id>/` — временные артефакты выполнения
- `logs/` — логи
- `tmp/` — временные файлы

### 6.3. Жёсткое правило

- Код **никогда** не размещается и не редактируется в `/srv`.
- Runtime‑артефакты **не считаются** источником истины.

---

## 7. Компоненты пайплайна (общее описание)

Каждый компонент:
- изолирован;
- не знает о n8n;
- тестируем независимо;
- взаимодействует только через контракт.

### 7.X BoundaryDetector (NEW)

**Назначение:**
Детерминированное определение границ статей на основе якорей, извлечённых из полного PDF.

**Вход:**
- anchors `{page, type, value, confidence}`
- `total_pages`
- versioned policy

**Выход:**
- диапазоны страниц `{id, from, to, evidence}`

**Гарантии:**
- отсутствие пересечений диапазонов;
- строгий детерминизм;
- fail‑fast при любой неоднозначности.

**Не отвечает за:**
- чтение PDF;
- физическую разрезку PDF;
- извлечение метаданных.

### Обновление Splitter

Splitter **не определяет** границы статей и работает исключительно по готовым диапазонам страниц, полученным от BoundaryDetector.

---

## 8. Ошибки и exit codes

| Exit code | Значение |
|---------|---------|
| 0 | success |
| 10 | invalid_input |
| 20 | extraction_failed |
| 30 | verification_failed |
| 40 | build_failed |
| 50 | internal_error |

---

## Appendix A. JSON Schemas (канонические контракты)

### A.X. boundary_ranges.json (MetadataExtractor → BoundaryDetector / BoundaryDetector → Splitter)
```json
{
  "status": "success",
  "component": "BoundaryDetector",
  "version": "1.0.0",
  "data": {
    "issue_id": "mg_2025_05_001",
    "ranges": [
      {"id": "a01", "from": 5, "to": 13},
      {"id": "a02", "from": 14, "to": 20}
    ]
  }
}
```

---

## ChangeLog

- Pipeline Flow обновлён: добавлен BoundaryDetector
- Splitter приведён к pure‑cutting ответственности
- Добавлен канонический контракт boundary_ranges.json

