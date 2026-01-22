# PDF Extractor — TechSpec v_2_5

**Статус:** Canonical (Self‑Contained)
**Дата:** 2026‑01‑22
**Предыдущая версия:** TechSpec v_2_4  

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

### Envelope Handling (Input)

Компоненты **должны** принимать envelope format от upstream:
```json
{
  "status": "success",
  "component": "UpstreamComponent",
  "version": "1.0.0",
  "data": {
    /* actual payload */
  },
  "error": null
}
```

**Правило unwrap** (обратная совместимость):
```python
raw = json.load(sys.stdin)
payload = raw.get("data", raw) if isinstance(raw, dict) else raw
# Validate and process payload
```

Это обеспечивает:
- Совместимость с upstream envelope output
- Fallback на raw format (если envelope отсутствует)
- Детерминизм (одинаковая обработка для обоих форматов)

### Stdout/Stderr Contract

**JSON output**: Только `stdout` (file descriptor 1)
- Использовать: `os.write(1, json_bytes)` или эквивалент с явным flush
- **НИКОГДА** в stderr

**Логи/ошибки**: Только `stderr` (file descriptor 2)
- Структурированные сообщения
- **НИКОГДА** JSON объекты в stderr

**Критично**: Соблюдение контракта проверяется в smoke tests (pipe/redirect режимы).

**Acceptance snippet**:
```bash
# Pipe mode
cat input.json | python component.py > out.json 2> err.log
# Redirect mode
python component.py < input.json > out.json 2> err.log

# Verify:
# - out.json: valid JSON, size > 0
# - err.log: empty (0 bytes) on success
# - exit code: 0
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

**Выход:**
- `article_starts`: `List[Dict]` — rich objects с метаданными:
  - `start_page` (int): номер страницы начала статьи (1-indexed)
  - `confidence` (float): уверенность детекции (фиксировано `1.0` для typography-based)
  - `signals` (dict): детерминированные сигналы обнаружения (policy constants only)
- `boundary_ranges`: `List[Dict]` — диапазоны для Splitter (сгенерированы из article_starts):
  - `id` (str): идентификатор статьи (a01, a02, ...)
  - `from` (int): начало диапазона (1-indexed, совпадает с start_page)
  - `to` (int): конец диапазона (1-indexed, inclusive)
  - **Инварианты**: contiguous, non-overlapping; последний range заканчивается на `total_pages`

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

### 8.1 ArticleStartPolicy v_1_0 (Canonical)
**Носитель политики:** BoundaryDetector.

**Метод детекции:** Typography-based (PRIMARY SIGNAL)
- Шрифт: `MyriadPro-BoldIt`
- Размер: `12.0 pt ± 0.5`
- Минимальная длина текста: 10 символов

**Фильтры:**
1. **Blacklist**: Исключение известных ложных срабатываний (номера выпусков, рубрики)
2. **RU/EN deduplication**: Удаление дублирующих заголовков (bilingual layout)
   - Consecutive pages: RU-dominant → EN-dominant
   - Text length similarity: 0.5x–2.0x ratio
   - Bilingual markers: KEYWORDS/ABSTRACT/INTRODUCTION на EN странице
   - **Результат**: сохраняется RU page, EN page исключается

**Канон:**
- Детекция детерминирована (typography match — binary, не вероятностная)
- DOI **не используется** как признак начала статьи
- Confidence фиксирован: `1.0` (match/no-match, без градации)
- Дедупликация применяется ко всем bilingual issues (e.g., mg_2025_12)

**Документация**: `docs/policies/article_start_detection_policy_v_1_0.md`

Любые изменения политики — только через новую версию policy (v_1_1+).

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
        "start_page": 5,
        "confidence": 1.0,
        "signals": {
          "primary": "typography_descriptor",
          "font_name": "MyriadPro-BoldIt",
          "font_size": 12.0,
          "tolerance": 0.5,
          "blacklist": [
            "2025. том 24. номер 12",
            "оригинальное исследование",
            "краткое сообщение"
          ],
          "ru_en_dedup_policy": "enabled"
        }
      },
      {
        "start_page": 6,
        "confidence": 1.0,
        "signals": {
          "primary": "typography_descriptor",
          "font_name": "MyriadPro-BoldIt",
          "font_size": 12.0,
          "tolerance": 0.5,
          "blacklist": [
            "2025. том 24. номер 12",
            "оригинальное исследование",
            "краткое сообщение"
          ],
          "ru_en_dedup_policy": "enabled"
        }
      }
    ],
    "boundary_ranges": [
      {"id": "a01", "from": 5, "to": 5},
      {"id": "a02", "from": 6, "to": 15}
    ]
  },
  "error": null
}
```

**Примечания к schema**:
- `confidence`: Фиксировано `1.0` (typography detection — детерминированный binary match)
- `signals.primary`: Указывает метод детекции (`"typography_descriptor"`)
- `signals.font_name`, `signals.font_size`, `signals.tolerance`: Из `ArticleStartPolicy v_1_0` (policy constants)
- `signals.blacklist`: Список запрещённых паттернов (из policy)
- `signals.ru_en_dedup_policy`: `"enabled"` | `"disabled"` (из policy.duplicate_filter_enabled)
- `boundary_ranges`: Генерируются из `article_starts`; `from == start_page`; contiguous/non-overlapping; последний `to == total_pages`

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

## ChangeLog (v_2_4)

- BoundaryDetector зафиксирован как **core‑компонент пайплайна**.
- MetadataExtractor зафиксирован как компонент, возвращающий **только сырые anchors** без политики и фильтрации.
- Добавлен раздел **Policy Dependencies**: ArticleStartPolicy v_1_0 как нормативная часть системы.
- Appendix A расширен контрактами для anchors и article_starts.

---

## ChangeLog (v_2_5)

**Дата:** 2026‑01‑22

**BoundaryDetector contract updates**:
- `article_starts` output: изменён с `List[int]` на `List[Dict]` (rich format)
  - Добавлены поля: `start_page` (int), `confidence` (float, fixed 1.0), `signals` (dict, deterministic)
  - Signals schema: typography-based (font_name, font_size, tolerance, blacklist, ru_en_dedup_policy)
- ArticleStartPolicy v_1_0: уточнён метод детекции (typography-based PRIMARY SIGNAL, не DOI/RU-blocks)
- RU/EN deduplication: документирована логика фильтрации bilingual duplicates (consecutive pages, text ratio, markers)
- `boundary_ranges`: инварианты явно зафиксированы (1-indexed, contiguous, non-overlapping, from==start_page, last to==total_pages)

**Inter-component communication**:
- Envelope unwrap pattern: документирован `raw.get("data", raw)` для обратной совместимости с upstream envelope/raw
- Stdout/stderr contract: явно зафиксирован (JSON → stdout via fd1, logs → stderr; обязательна проверка в pipe/redirect modes)

**Appendix A updates**:
- A.3 article_starts.json: обновлён пример с typography-based signals (заменяет старый DOI/RU-blocks пример)
- Добавлены примечания к signals schema (детерминизм, policy constants, boundary_ranges invariants)

**Implementation commits** (reference):
- `62b9315`: feat(boundary): implement typography-based article detection
- `56c8a98`: feat(boundary): unwrap envelope + RU/EN dedup
- `431c0a2`: fix(boundary): harden JSON emit to stdout (fd1)
- `beb05af`: fix(boundary): emit rich article_starts objects

