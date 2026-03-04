# PDF Extractor — TechSpec v_2_8

**Статус:** Canonical (Self‑Contained)
**Дата:** 2026‑03‑04
**Предыдущая версия:** TechSpec v_2_7

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
- `inbox/` — входящие PDF до запуска пайплайна (landing zone; см. §6.4)
- `runs/<issue_id>_<run_id>/` — временные артефакты выполнения (input.json, step outputs, logs)
- `exports/<JournalCode>/<YYYY>/<IssuePrefix>/exports/<export_id>/` — финальные артефакты (articles/, manifest/, checksums.sha256)
- `logs/` — логи
- `tmp/` — временные файлы

### 6.3 Жёсткое правило

- Код **никогда** не размещается и не редактируется в `/srv`.
- Runtime‑артефакты **не считаются** источником истины.

### 6.4 Input Delivery: inbox/

**Canonical input path:** `/srv/pdf-extractor/inbox/`

Директория предназначена для хранения входящих PDF до момента запуска пайплайна (landing zone). После доставки PDF оператор передаёт путь в `run_issue_pipeline.sh` через `--pdf-path`.

**Naming convention:**

```
{JournalCode}_{YYYY}-{NN}.pdf
```

Примеры: `Na_2026-02.pdf`, `Mg_2025-12.pdf`, `Mh_2026-02.pdf`
Формат совпадает с `IssuePrefix` из [Filename Generation Policy](../../policies/filename_generation_policy_v_1_2.md).

**Доставка:**

Оператор копирует PDF с локальной машины через `scp` (Git Bash на PC):

```bash
scp <local_file>.pdf dmitry@2.58.98.101:/srv/pdf-extractor/inbox/{JournalCode}_{YYYY}-{NN}.pdf
```

**Права доступа:**

| Параметр | Значение |
|---|---|
| Путь | `/srv/pdf-extractor/inbox/` |
| Владелец | `dmitry:dmitry` |
| Права директории | `drwxrwxr-x` (775) |

**Политика хранения и очистки:**

Пайплайн **не удаляет** PDF из `inbox/` автоматически. PDF удаляется вручную оператором после выполнения всех условий:

1. Export завершён без ошибок (`exit code = 0`)
2. Инвариант `T=L=E` подтверждён
3. `checksums.sha256` верифицирован
4. Артефакты скопированы на PC (при необходимости)

До выполнения условий 1–4 PDF остаётся в `inbox/` (защита от потери входных данных при сбое или повторном прогоне).

**Уникальность файлов:**

Если файл с тем же именем уже существует в `inbox/`, оператор обязан:
- убедиться, что это тот же файл (сравнить sha256), **или**
- переименовать новый файл до копирования.

Автоматического контроля уникальности нет (planned).

**Data flow:**

```
scp → /srv/pdf-extractor/inbox/{JournalCode}_{YYYY}-{NN}.pdf
                       ↓
tools/run_issue_pipeline.sh \
  --journal-code <code> \
  --issue-id <id> \
  --pdf-path /srv/pdf-extractor/inbox/{JournalCode}_{YYYY}-{NN}.pdf
                       ↓
/srv/pdf-extractor/runs/{issue_id}_{run_id}/
  input/input.json
  outputs/01.json … 08.json
  logs/01.log … 08.log
                       ↓
/srv/pdf-extractor/exports/{JournalCode}/{YYYY}/{IssuePrefix}/exports/{export_id}/
  articles/            ← финальные PDF (canonical naming)
  manifest/            ← export_manifest.json
  checksums.sha256
  README.md
```

**Замечание о runner:** `tools/run_issue_pipeline.sh` принимает `--pdf-path <любой читаемый путь>` — runner не проверяет директорию источника. `inbox/` является конвенциональным входным путём для оператора.

**Evidence:** Na_2026-02 (2026-03-04) — PDF загружен в `inbox/`, обработан через `run_issue_pipeline.sh`, `T=L=E=6`, sha256 verified.

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

#### 7.3.1 Anchor Types

MetadataExtractor извлекает следующие типы anchors:

**Structural anchors:**
- `doi` — Digital Object Identifier
- `text_block` — typography-based text blocks (font_name, font_size, bbox)

**Language-specific metadata (bilingual journals):**
- `ru_title` — Russian article title
- `ru_authors` — Russian author list (format: `Фамилия И.О., Фамилия И.О.`)
- `ru_affiliations` — Russian affiliations
- `ru_address` — Russian correspondence address
- `ru_abstract` — Russian abstract
- `en_title` — English article title
- `en_authors` — English author list (format: `Surname I.I., Surname I.I.`)
- `en_affiliations` — English affiliations
- `en_address` — English correspondence address
- `en_abstract` — English abstract

**Section markers:**
- `contents_marker` — table of contents indicator
- `section_marker` — section headers (Keywords, Abstract, etc.)

#### 7.3.2 Separation Rules: ru_title vs ru_authors

**Critical requirement:** `ru_title` и `ru_authors` **must be separate anchors**.

**Detection rules (deterministic):**
1. **ru_title:**
   - Typography: MyriadPro-BoldIt, 12.0 pt ± 0.5
   - Position: upper portion of page
   - Content: article title text (long descriptive phrase)

2. **ru_authors:**
   - Typography: MyriadPro-Bold, ~9 pt (smaller than title)
   - Position: below ru_title (vertical ordering: y0_authors > y0_title)
   - Content: author list with initials pattern (`И.О.` or `,`)
   - **Exclusion filter:** text must NOT match ru_title text (text-based exclusion)
   - **Semantic filter:** text with ≥3 lowercase words AND no initials → likely title, not authors

**Example (page 110, Mg_2025-12):**
```json
{
  "page": 110,
  "type": "ru_title",
  "text": "Патогенетика сочетанных форм бронхиальной астмы с сердечно-сосудистыми...",
  "bbox": [56.69, 107.37, 482.25, 136.22]
}
{
  "page": 110,
  "type": "ru_authors",
  "text": "Брагина Е.Ю.",
  "bbox": [56.69, 140.78, 110.91, 151.93]
}
```

**Anti-pattern (violation):**
```json
❌ ru_title text appearing in ru_authors anchor
```

#### 7.3.3 Extraction Invariants

- **Determinism:** Same PDF → same anchors (positions, types, text)
- **No filtering:** All observed anchors emitted (no selective omission)
- **No interpretation:** MetadataExtractor does NOT determine article boundaries or material classification
- **Fail-fast:** Exit 20 (extraction_failed) on PDF parsing errors

### 7.4 BoundaryDetector (Core)
**Назначение:** детерминированное определение границ статей на основе anchors, извлечённых из полного PDF.

**Вход:** anchors + `total_pages` + versioned policy.

**Выход:**
- `article_starts`: `List[Dict]` — rich objects с метаданными:
  - `start_page` (int): номер страницы начала статьи (1-indexed)
  - `confidence` (float): уверенность детекции (фиксировано `1.0` для typography-based)
  - `signals` (dict): детерминированные сигналы обнаружения (policy constants only)
  - `material_kind` (str): тип материала (`contents`, `editorial`, `research`, `digest`)
- `boundary_ranges`: `List[Dict]` — диапазоны для Splitter (сгенерированы из article_starts):
  - `id` (str): идентификатор статьи (a01, a02, ...)
  - `from` (int): начало диапазона (1-indexed, совпадает с start_page)
  - `to` (int): конец диапазона (1-indexed, inclusive)
  - `material_kind` (str): тип материала
  - **Инварианты**: contiguous, non-overlapping; последний range заканчивается на `total_pages`

**Гарантии:**
- строгий детерминизм;
- отсутствуют пересечения/дубликаты стартов;
- fail‑fast при неоднозначности в рамках политики.

**Не отвечает за:**
- чтение/парсинг PDF;
- физическую разрезку PDF;
- извлечение anchors.

#### 7.4.1 Material Classification

BoundaryDetector классифицирует каждую обнаруженную статью по типу материала:

**Material kinds:**
- `contents` — Table of contents (multi-page, front matter)
- `editorial` — Editorial/foreword (no extractable authors)
- `research` — Research article (with extractable first author)
- `digest` — Digest/summary materials (journal-specific)
- `info` — Editorial guidelines / journal announcements (added 2026-02-21)

**Classification rules:**
1. **Contents detection** (special case, front matter):
   - Triggered by `contents_marker` anchor on pages 1-4
   - **Temporary heuristic:** `max_page=4` constraint (may be revised for other journals)

2. **Editorial detection:**
   - Article start WITHOUT extractable authors on same page (window=0)
   - **Temporary heuristic:** Filters editorial greetings/signatures by pattern matching
   - Examples: "Уважаемые коллеги", academic titles, length > 200 chars

3. **Research detection:**
   - Article start WITH extractable authors in window [page, page+1]
   - Authors: `ru_authors` or `en_authors` anchors (after editorial filtering)

4. **Info detection** (NEW):
   - Standalone «ИНФОРМАЦИЯ» / «INFORMATION» `text_block` on page **AND** no article-level DOI on page
   - Distinguishes: section heading «ИНФОРМАЦИЯ» (research, has DOI) vs info section heading (info, no DOI)
   - Implementation: `_is_info_section_page()` in `agents/boundary_detector/detector.py`

**Note on heuristics:**
- Contents `max_page=4` — empirical constraint for current journal stack
- Editorial greeting filter — partial detector, not comprehensive policy
- These heuristics are **temporary** and may require refinement for broader journal coverage

**Determinism:** Material classification is rule-based (not probabilistic), but heuristics may evolve.

### 7.5 Splitter
**Назначение:** физическая разрезка PDF **строго по готовым диапазонам**, полученным от BoundaryDetector.

**Канон:** Splitter **не определяет** границы статей.

### 7.6 MetadataVerifier
**Назначение:** проверка согласованности метаданных и артефактов article‑PDF с ожиданиями пайплайна; обогащение метаданных для OutputBuilder.

**Функции:**
- Validation: required fields, page ranges, file existence, naming rules
- Enrichment: `first_author_surname`, `expected_filename`, journal/issue metadata
- Material-aware processing: research articles (surname extraction) vs service materials (fixed suffixes)

**Filename generation:** См. `docs/policies/filename_generation_policy_v_1_0.md`

**Key logic (RU-journals):**
1. **Research articles:**
   - Extract `first_author_surname` from anchors
   - **Priority:** ru_authors (transliterated) → en_authors (validated)
   - **Validation:** reject gene symbols (TPM1, LPL), rsID patterns (rs1143634)
   - **Format:** `{IssuePrefix}_{PPP-PPP}_{Surname}.pdf`

2. **Service materials:**
   - **Format:** `{IssuePrefix}_{PPP-PPP}_{ServiceSuffix}.pdf`
   - Suffixes: `Contents`, `Editorial`, `Digest`

**Evidence tracking:** All surname extractions include `first_author_surname_source` and `evidence` fields for audit trail.

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
      "page": 1,
      "type": "contents_marker",
      "text": "СОДЕРЖАНИЕ",
      "lang": "ru",
      "bbox": [56.69, 80.50, 150.20, 95.30],
      "confidence": 0.9
    },
    {
      "page": 6,
      "type": "doi",
      "value": "10.25557/2073-7998.2025.12.6-15",
      "confidence": 0.98,
      "bbox": [0, 0, 0, 0]
    },
    {
      "page": 6,
      "type": "ru_title",
      "text": "Полиморфизм генов ренин-ангиотензиновой системы...",
      "lang": "ru",
      "bbox": [56.69, 107.37, 482.25, 136.22],
      "confidence": 0.9
    },
    {
      "page": 6,
      "type": "ru_authors",
      "text": "Гандаева М.С., Коробова З.Р.",
      "lang": "ru",
      "bbox": [56.69, 140.78, 180.50, 151.93],
      "confidence": 0.9
    },
    {
      "page": 6,
      "type": "en_title",
      "text": "Polymorphism of renin-angiotensin system genes...",
      "lang": "en",
      "bbox": [56.69, 250.40, 480.12, 275.80],
      "confidence": 0.9
    },
    {
      "page": 6,
      "type": "en_authors",
      "text": "Gandaeva M.S., Korobova Z.R.",
      "lang": "en",
      "bbox": [56.69, 280.15, 185.30, 290.50],
      "confidence": 0.9
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

**Примечания к anchor types:**
- `ru_title`, `ru_authors` — RU-metadata (bilingual journals)
- `en_title`, `en_authors` — EN-metadata (bilingual journals)
- `contents_marker` — front matter detection (Contents section)
- `ru_title` и `ru_authors` — **строго разделены** (разный text, разная bbox)

### A.3 article_starts.json (BoundaryDetector output)
```json
{
  "status": "success",
  "component": "BoundaryDetector",
  "version": "1.2.0",
  "data": {
    "issue_id": "mg_2025_12",
    "total_pages": 156,
    "article_starts": [
      {
        "start_page": 1,
        "confidence": 1.0,
        "material_kind": "contents",
        "signals": {
          "primary": "contents_marker_on_first_pages",
          "detection_method": "special_case_front_matter"
        }
      },
      {
        "start_page": 5,
        "confidence": 1.0,
        "material_kind": "editorial",
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
        "material_kind": "research",
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
      {"id": "a01", "from": 1, "to": 4, "material_kind": "contents"},
      {"id": "a02", "from": 5, "to": 5, "material_kind": "editorial"},
      {"id": "a03", "from": 6, "to": 15, "material_kind": "research"}
    ]
  },
  "error": null
}
```

**Примечания к schema**:
- `confidence`: Фиксировано `1.0` (typography detection — детерминированный binary match)
- `material_kind`: `contents` | `editorial` | `research` | `digest` (classification by BoundaryDetector)
- `signals.primary`: Указывает метод детекции (`"typography_descriptor"` или `"contents_marker_on_first_pages"`)
- `signals.font_name`, `signals.font_size`, `signals.tolerance`: Из `ArticleStartPolicy v_1_0` (policy constants)
- `signals.blacklist`: Список запрещённых паттернов (из policy)
- `signals.ru_en_dedup_policy`: `"enabled"` | `"disabled"` (из policy.duplicate_filter_enabled)
- `boundary_ranges`: Генерируются из `article_starts`; `from == start_page`; contiguous/non-overlapping; последний `to == total_pages`; включают `material_kind`

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

## ChangeLog (v_2_7)

**Дата:** 2026‑02‑21

**`info` material_kind** (§7.4.1):
- Добавлен `info` в перечень material_kinds: editorial guidelines / journal announcements
- Classification rule 4 (Info detection): standalone ИНФОРМАЦИЯ/INFORMATION text_block + нет DOI
- Семантика: рубрика с DOI → `research`; заголовок раздела без DOI → `info`
- Implementation: `_is_info_section_page()` в `agents/boundary_detector/detector.py` v1.3.1

**Acceptance validation** (Mh_2026-02):
- Issue: Mh_2026-02 (9 articles: 1 Contents + 7 Research + 1 Info)
- T=L=E=9, sha256 verified
- Export: `/srv/pdf-extractor/exports/Mh/2026/Mh_2026-02/exports/2026_02_21__19_04_46/`

**Policy updates:**
- `filename_generation_policy_v_1_2.md` — добавлен `info` → `_Info.pdf` suffix
- `boundary_detector_v_1_3.md` — задокументирован `info` material_kind

**Implementation commits** (reference):
- `9ac5c59`: fix(pipeline): fix Mh_2026-02 — Skryabin surname + Info section detection
- `e817eef`: fix(boundary_detector): v1.3.1 — fix info detection, revert en_authors filter

---

## ChangeLog (v_2_6)

**Дата:** 2026‑01‑27

**MetadataExtractor anchor types documentation** (§7.3):
- Документированы все типы anchors: structural (doi, text_block), language-specific (ru_title, ru_authors, en_title, en_authors), section markers (contents_marker)
- Добавлены правила разделения ru_title и ru_authors (§7.3.2):
  - Typography-based detection (font size, position)
  - Text-based exclusion (ru_title text must not appear in ru_authors)
  - Semantic filter (lowercase words + no initials → title, not authors)
- Добавлены extraction invariants (§7.3.3): determinism, no filtering, no interpretation

**Material Classification** (§7.4.1):
- Документирована классификация material_kind: `contents`, `editorial`, `research`, `digest`
- Classification rules:
  - Contents: special case detection (contents_marker on pages 1-4, **temporary heuristic:** max_page=4)
  - Editorial: article start without extractable authors (window=0, **temporary heuristic:** greeting filter)
  - Research: article start with extractable authors (window [page, page+1])
- **Явно помечены временные эвристики**: max_page=4, editorial greeting filter (may be revised for broader journal coverage)

**MetadataVerifier enrichment** (§7.6):
- Документирована функция обогащения метаданных: first_author_surname, expected_filename
- Filename generation policy: RU-journals priority (ru_authors → en_authors)
- Validation: gene/rsID rejection (TPM1, LPL, rs1143634)
- Reference: `docs/policies/filename_generation_policy_v_1_0.md`

**Appendix A updates**:
- A.2 anchors.json: добавлены примеры ru_title, ru_authors, en_title, en_authors, contents_marker
- A.3 article_starts.json: добавлено поле material_kind в article_starts и boundary_ranges
- Обновлён BoundaryDetector version reference: 1.2.0

**Policy documents** (new):
- Создан `docs/policies/filename_generation_policy_v_1_0.md` (canonical, RU-journals)

**Implementation commits** (reference):
- `b9f215d`: feat(material): implement RU-journal filename policy and fix classification issues

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

---

## ChangeLog (v_2_8)

**Дата:** 2026‑03‑04

**RFC-4: inbox/ — canonical input path** (§6.2, §6.4 new):

- §6.2 Runtime layout: добавлены строки `inbox/` и полный путь `exports/`
- §6.4 (новый раздел): Input Delivery — canonical path `/srv/pdf-extractor/inbox/`, naming convention `{JournalCode}_{YYYY}-{NN}.pdf`, delivery via scp, access rights (`dmitry:dmitry`, 775), retention/cleanup policy (manual, after T=L=E + sha256 + PC copy), uniqueness policy, full data flow diagram

**Замечание:** `tools/run_issue_pipeline.sh` принимает `--pdf-path <любой путь>`; `inbox/` — конвенциональный входной путь оператора, runner не валидирует директорию источника.

**Evidence:** Na_2026-02 (2026-03-04), T=L=E=6, sha256 verified; `inbox/Na_2026-02.pdf` — первый production прогон через `inbox/`.
