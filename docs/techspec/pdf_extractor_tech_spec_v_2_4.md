# PDF Extractor — TechSpec v2.4

**Статус:** Canonical (Self‑Contained)  
**Дата:** 2025‑12‑28  
**Предыдущая версия:** TechSpec v2.3.1  

---

## 1. Назначение документа

Данный документ является **единственным и самодостаточным техническим заданием (TechSpec)** проекта **PDF Extractor**.

Документ:
- не требует обращения к предыдущим версиям;
- содержит полное описание архитектуры, инвариантов, пайплайна и контрактов;
- предназначен для прямой передачи разработчику как каноническое ТЗ.

---

## 2. Архитектурные инварианты (NON‑NEGOTIABLE)

1. **Python‑only.** Вся вычислительная, проверочная и трансформационная логика реализуется исключительно на Python.
2. **n8n — только оркестратор.** Любая бизнес‑логика, проверки или ветвления в n8n запрещены.
3. **LLM отсутствует в runtime.** Использование LLM допускается только на этапе проектирования/документации.
4. **Детерминизм.** Одинаковый вход → одинаковый выход.
5. **Fail‑fast.** Любая ошибка выражается комбинацией `exit code` + структурированный JSON; пайплайн останавливается немедленно.
6. **Инвариант T = L = E (консистентность артефактов).**
   - **T** — количество статей в итоговом JSON;
   - **L** — количество имён файлов;
   - **E** — количество реально созданных PDF.
   Нарушение инварианта → `exit code 30 (verification_failed)`.
7. **Code ≠ Runtime.** Код и runtime‑артефакты физически и логически разделены.
8. **Один центр правды (SoT).** Исходники кода и документации в репозитории являются единственным источником истины; runtime‑артефакты не являются SoT.

---

## 3. Роль инструментов

- **Python:** реализация всех core‑компонентов пайплайна.
- **n8n:** линейная оркестрация вызовов Python‑команд и сбор статусов.
- **Storage (Supabase / FS):** хранение исходных PDF и итоговых артефактов.

---

## 4. Канонический Pipeline Flow (строгая последовательность)

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

## 5. Межкомпонентное взаимодействие

- **Вход:** JSON через `stdin`
- **Выход:** JSON через `stdout`
- **Логи:** `stderr`
- **Бинарные данные:** ссылки на storage (Supabase / FS)

### Единый формат ответа (все компоненты)

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

### 6.1 Code — Source of Truth

`/opt/projects/pdf-extractor/`

- `agents/` — Python core‑компоненты пайплайна
- `tests/` — unit и golden‑тесты
- `docs/` — TechSpec, Plan, policies, summaries

Код хранится в Git и является **единственным источником истины**.

### 6.2 Runtime — НЕ Source of Truth

`/srv/pdf-extractor/`

- `venv/` — виртуальное окружение Python
- `runs/<run_id>/` — временные артефакты выполнения
- `logs/` — логи
- `tmp/` — временные файлы

### 6.3 Жёсткое правило

- Код **никогда** не размещается и не редактируется в `/srv`.
- Runtime‑артефакты **не считаются** источником истины.

---

## 7. Компоненты пайплайна (ответственность)

Каждый компонент:
- изолирован;
- не знает о n8n;
- тестируем независимо;
- взаимодействует только через контракт.

### 7.1 InputValidator
**Назначение:** проверка валидности входного файла (PDF), базовый smoke‑check.

### 7.2 PDFInspector
**Назначение:** получение структурной информации о PDF (минимум: `total_pages`).

### 7.3 MetadataExtractor (FULL PDF)
**Назначение:** извлечение **сырых anchors** (наблюдаемых фактов) по всему PDF.

**Канон (важно):**
- MetadataExtractor **не применяет политику**.
- MetadataExtractor **не фильтрует** DOI и другие anchors.
- Выход — только наблюдения (layout/типографика/языковые маркеры/секционные маркеры и т.п.) без интерпретации.

### 7.4 BoundaryDetector (Core)
**Назначение:** детерминированное определение границ статей на основе anchors, извлечённых из полного PDF.

**Вход:** anchors + `total_pages` + versioned policy.

**Выход:** `article_starts` и производные диапазоны/границы для Splitter.

**Гарантии:**
- строгий детерминизм;
- отсутствуют пересечения/дубликаты стартов;
- fail‑fast при неоднозначности в рамках политики.

**Не отвечает за:**
- чтение/парсинг PDF;
- физическую разрезку PDF;
- извлечение anchors.

### 7.5 Splitter
**Назначение:** физическая разрезка PDF **строго по готовым диапазонам**, полученным от BoundaryDetector.

**Канон:** Splitter **не определяет** границы статей.

### 7.6 MetadataVerifier
**Назначение:** проверка согласованности метаданных и артефактов article‑PDF с ожиданиями пайплайна.

### 7.7 OutputBuilder
**Назначение:** формирование итоговых файлов и структуры выдачи.

### 7.8 OutputValidator
**Назначение:** финальная валидация результатов и инварианта `T = L = E`.

---

## 8. Policy Dependencies (канонические политики)

Пайплайн использует versioned policies. Политика — часть системы, обязательна для воспроизводимости и аудита.

### 8.1 ArticleStartPolicy v1.0 (Canonical)
**Носитель политики:** BoundaryDetector.

**Канон:**
- DOI **никогда** не является достаточным одиночным признаком начала статьи.
- Решение принимается **только** по совокупности сигналов (RU‑структура, layout, типографика, маркеры секций, anti‑signals).

Любые изменения политики — только через новую версию policy (v1.1+).

---

## 9. Ошибки и exit codes

| Exit code | Значение |
|---------:|----------|
| 0 | success |
| 10 | invalid_input |
| 20 | extraction_failed |
| 30 | verification_failed |
| 40 | build_failed |
| 50 | internal_error |

---

## Appendix A. JSON Schemas (канонические контракты)

### A.1 response_envelope.json (общий envelope)
```json
{
  "status": "success",
  "component": "ComponentName",
  "version": "1.0.0",
  "data": {},
  "error": null
}
```

### A.2 anchors.json (MetadataExtractor → BoundaryDetector)
```json
{
  "issue_id": "mg_2025_12",
  "total_pages": 156,
  "anchors": [
    {
      "page": 6,
      "type": "doi",
      "value": "10.25557/2073-7998.2025.12.6-15",
      "confidence": 0.98,
      "bbox": [0, 0, 0, 0]
    },
    {
      "page": 6,
      "type": "text_block",
      "text": "...",
      "language": "ru",
      "font_size": 14.0,
      "font_weight": "bold",
      "bbox": [0, 0, 0, 0]
    },
    {
      "page": 6,
      "type": "section_marker",
      "value": "Аннотация",
      "language": "ru",
      "bbox": [0, 0, 0, 0]
    }
  ]
}
```

### A.3 article_starts.json (BoundaryDetector output)
```json
{
  "status": "success",
  "component": "BoundaryDetector",
  "version": "1.0.0",
  "data": {
    "issue_id": "mg_2025_12",
    "total_pages": 156,
    "article_starts": [
      {
        "start_page": 6,
        "confidence": 0.97,
        "signals": {
          "ru_title": true,
          "ru_authors": true,
          "ru_affiliations": true,
          "ru_address": true,
          "ru_abstract": true,
          "optional_ru_blocks": ["keywords_ru", "for_citation_ru"],
          "doi_publisher_structured": true,
          "doi_value": "10.25557/2073-7998.2025.12.6-15",
          "en_block_present": true,
          "constraints": {
            "page_position_top_40": true,
            "ru_title_max_font_on_page": true,
            "canonical_sequence_ru": true
          },
          "anti_signals": []
        }
      }
    ]
  },
  "error": null
}
```

### A.4 boundary_ranges.json (BoundaryDetector → Splitter)
```json
{
  "status": "success",
  "component": "BoundaryDetector",
  "version": "1.0.0",
  "data": {
    "issue_id": "mg_2025_12",
    "ranges": [
      {"id": "a01", "from": 5, "to": 13},
      {"id": "a02", "from": 14, "to": 20}
    ]
  },
  "error": null
}
```

---

## ChangeLog (v2.4)

- BoundaryDetector зафиксирован как **core‑компонент пайплайна**.
- MetadataExtractor зафиксирован как компонент, возвращающий **только сырые anchors** без политики и фильтрации.
- Добавлен раздел **Policy Dependencies**: ArticleStartPolicy v1.0 как нормативная часть системы.
- Appendix A расширен контрактами для anchors и article_starts.

