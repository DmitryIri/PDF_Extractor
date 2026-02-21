# PDF Extractor — BoundaryDetector v_1_3

**Project:** PDF Extractor
**Phase:** 2.4 BoundaryDetector
**Status:** Canonical
**Version:** v_1_3
**Date:** 2026-02-21
**Depends on:**
- PDF Extractor — ArticleStartPolicy v_1_0
- PDF Extractor — TechSpec v_2_7 §7.4.1 (Material Classification)
- PDF Extractor — FilenameGenerationPolicy v_1_2 (material_kind usage)
**Previous version:** v_1_2

---

## 1. Цель компонента

BoundaryDetector v_1_3 — детерминированный компонент, который принимает **сырые anchors** (наблюдаемые факты из PDF) и применяет **ArticleStartPolicy v_1_0** для определения:

- страниц начала каждой статьи (article start pages),
- **классификации материала (material_kind: contents/editorial/research/digest/info)** ⭐ info добавлен в v_1_3,
- уверенности (confidence) для каждой границы,
- набора сработавших сигналов (signals) для аудита и отладки.

BoundaryDetector не режет PDF и не извлекает текст «заново» — он **только интерпретирует anchors**.

---

## 2. BoundaryDetector I/O Contract

### 2.1 Вход: Anchors JSON

BoundaryDetector принимает JSON-объект следующего общего вида:

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

#### 2.1.1 Обязательные поля

- `issue_id` (string): идентификатор выпуска.
- `total_pages` (int): общее число страниц в PDF.
- `anchors` (array): список anchors.

#### 2.1.2 Требования к anchors (минимальный набор для v_1_0)

BoundaryDetector v_1_0 требует, чтобы в anchors присутствовали **как минимум**:

1) `type="doi"`  
- `value`: строка DOI (без нормализации в верхний/нижний регистр)
- `page`: номер страницы (1-based)

2) `type="text_block"`  
- `text`: текст блока
- `language`: `ru|en|unknown`
- `font_size`: числовое значение
- `font_weight`: `normal|bold|unknown`
- `bbox`: координаты блока на странице (в системе координат PDF)

3) `type="section_marker"` (или эквивалентный тип)  
- `value`: маркеры секций, по которым можно детектировать RU/EN структуру:
  - RU: "Аннотация", "Ключевые слова", "Для цитирования" и т.п.
  - EN: "Abstract", "Keywords", "For citation", "Corresponding author" и т.п.

Примечание: если `section_marker` отсутствует, допускается детект через `text_block` по ключевым фразам (см. алгоритм), но в таком случае confidence понижается согласно правилам.

---

### 2.2 Выход: Article Boundaries JSON

BoundaryDetector возвращает JSON следующего общего вида:

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

#### 2.2.1 Поля результата

- `article_starts` (array): список найденных начал статей (rich objects).
  - `start_page` (int): номер страницы начала статьи (1-indexed).
  - `confidence` (float): уверенность детекции (фиксировано `1.0` для typography-based).
  - **`material_kind` (str):** классификация материала
    - `"contents"` — table of contents (multi-page front matter)
    - `"editorial"` — editorial/foreword (без извлекаемых авторов)
    - `"research"` — research article (с извлекаемыми авторами)
    - `"digest"` — digest/summary materials (journal-specific, если реализовано)
    - `"info"` — editorial guidelines / journal announcements ⭐ NEW in v_1_3
  - `signals` (dict): детерминированные сигналы обнаружения (policy constants):
    - `primary`: метод детекции (`"typography_descriptor"` или `"contents_marker_on_first_pages"` для Contents).
    - `font_name`, `font_size`, `tolerance`: параметры типографики из ArticleStartPolicy v_1_0.
    - `blacklist`: список запрещённых паттернов (из policy).
    - `ru_en_dedup_policy`: `"enabled"` | `"disabled"` (из policy.duplicate_filter_enabled).
- `boundary_ranges` (array): диапазоны для Splitter (сгенерированы из article_starts).
  - `id` (str): идентификатор статьи (a01, a02, ...).
  - `from` (int): начало диапазона (1-indexed, совпадает с start_page).
  - `to` (int): конец диапазона (1-indexed, inclusive).
  - **`material_kind` (str):** классификация материала (см. выше)
  - **Инварианты**: contiguous, non-overlapping; последний range заканчивается на `total_pages`.

#### 2.2.2 Гарантии

- `article_starts` отсортирован по `start_page` по возрастанию.
- Значения `start_page` уникальны.
- Первая найденная статья не может иметь `start_page < 1` или `> total_pages`.
- `confidence` фиксирован: всегда `1.0` (typography-based detection — binary match).
- `boundary_ranges` генерируются детерминированно из `article_starts`:
  - 1-indexed, contiguous, non-overlapping.
  - `from == start_page` для каждого range.
  - Последний `to == total_pages`.

---

## 3. Детерминированный алгоритм BoundaryDetector v_1_2 (Typography-based + Material Classification)

Алгоритм основан на ArticleStartPolicy v_1_0 (Typography-based) и состоит из трёх стадий, дополненных material classification:

1) Извлечение typography candidates (PRIMARY SIGNAL)
2) Применение фильтров (blacklist, RU/EN deduplication)
3) Генерация boundary_ranges

---

### 3.1 Стадия 1 — Подготовка данных (per-page model)

#### Шаг 1. Сгруппировать anchors по `page`
Для каждой страницы `p` сформировать структуру:
- `page_dois[]`
- `page_text_blocks[]`
- `page_markers[]`
- `page_font_stats` (max_font_size, distribution)
- `page_regions` (top_40%, middle, bottom) — определяется по `bbox`

#### Шаг 2. Построить статистику шрифта на странице
- `max_font_size_on_page(p)`
- список `top_candidates_by_font_size(p)` — text_block с максимальным font_size

#### Шаг 3. Определить «верхнюю зону» страницы
- высота страницы считается по координатам PDF.
- `top_40%` — диапазон `y <= 0.40 * page_height`.

---

### 3.2 Стадия 2 — Typography-based Candidate Extraction (PRIMARY SIGNAL)

BoundaryDetector v_1_1 использует **единственный источник кандидатов**: typography descriptor.

#### PRIMARY SIGNAL: Typography Marker

Страница `p` становится кандидатом начала статьи, если на ней найден text_block, удовлетворяющий **всем** условиям:

1. `font_name == "MyriadPro-BoldIt"`
2. `11.5 <= font_size <= 12.5` (12.0 ± 0.5 tolerance)
3. `len(text) >= 10` символов

**Детерминизм**: Typography match — binary (true/false), не вероятностный.

**Канон** (из ArticleStartPolicy v_1_0):
- DOI **не используется** как признак начала статьи.
- RU-блоки (title/authors/affiliations/address/abstract) **не используются** в v_1_1.
- Единственный надёжный инвариант: typography descriptor.

#### Фильтр 1: Blacklist

Кандидаты исключаются, если text содержит (case-insensitive match) один из паттернов:
- "2025. том 24. номер 12" (номер выпуска)
- "оригинальное исследование" (рубрика)
- "краткое сообщение" (рубрика)

#### Фильтр 2: RU/EN Deduplication (Bilingual Layout)

Если кандидаты обнаружены на consecutive pages `p` и `p+1`:
- page `p` — RU-dominant (>= 50% cyrillic letters)
- page `p+1` — EN-dominant (>= 50% latin letters)
- Text length ratio: 0.5x–2.0x
- page `p+1` содержит bilingual markers (KEYWORDS/ABSTRACT/INTRODUCTION)

**Результат**: сохраняется page `p` (RU), исключается page `p+1` (EN duplicate).

---

### 3.3 Стадия 3 — Confidence и Signals (Deterministic)

#### 3.3.1 Confidence (Fixed)

Для typography-based detection confidence **фиксирован**:

```
confidence = 1.0
```

**Обоснование**:
- Typography match — binary decision (true/false), не вероятностная оценка.
- Кандидат либо соответствует PRIMARY SIGNAL (font_name + font_size + text_length), либо нет.
- Нет градации уверенности; нет порогов принятия (threshold).

#### 3.3.2 Signals (Policy Constants)

Для каждого найденного start_page генерируется signals object:

```json
{
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
```

**Примечания**:
- Все поля — policy constants (из ArticleStartPolicy v_1_0).
- `ru_en_dedup_policy` отражает состояние policy, не per-item решение.
- Нет boolean RU-blocks flags (`ru_title`, `ru_authors`, etc.) — они не используются в v_1_1.

---

#### 3.3.3 DOI Policy Clarification (v_1_1)

**ВАЖНО**: BoundaryDetector v_1_1 **не использует DOI** как признак начала статьи.

**Обоснование** (из ArticleStartPolicy v_1_0):
- DOI **не является** надёжным инвариантом начала статьи.
- DOI может отсутствовать, быть повреждён, или находиться в References.
- Единственный надёжный инвариант: typography descriptor (PRIMARY SIGNAL).

**Статус DOI в v_1_1**:
- DOI anchors игнорируются при candidate generation.
- DOI не влияет на confidence (фиксирован 1.0).
- DOI может извлекаться MetadataExtractor, но не используется BoundaryDetector для recognition.

---

### 3.4 Генерация boundary_ranges

После фильтрации candidates:

1) **article_starts**: Список start_page с фиксированным confidence=1.0 и signals (policy constants).
2) **boundary_ranges**: Генерируются детерминированно из article_starts:
   - `id`: a01, a02, ... (sequential)
   - `from`: start_page (1-indexed)
   - `to`: до следующего start_page - 1, или до total_pages для последнего range
   - Инварианты: 1-indexed, contiguous, non-overlapping; `from == start_page`; последний `to == total_pages`

### 3.5 Финальная консолидация article_starts

После обработки кандидатов:

1) Отсортировать по `start_page` (возрастание).
2) Удалить дубликаты (если применимо).
3) Проверить монотонность: start_page строго возрастают.
4) Проверить уникальность: нет двух статей с одинаковым start_page.

---

### 3.6 Material Classification and Front-Matter Handling

⭐ **NEW in v_1_2**

После применения PRIMARY SIGNAL (typography-based detection) и фильтров, BoundaryDetector классифицирует каждую обнаруженную статью по типу материала (`material_kind`).

**Downstream usage:**
- **MetadataVerifier:** Определяет стратегию генерации filename (research vs service materials).
- **OutputBuilder:** Создаёт filename с service suffix (`_Contents.pdf`, `_Editorial.pdf`).

См.: `docs/policies/filename_generation_policy_v_1_0.md` для правил именования по material_kind.

---

#### 3.6.1 Contents (material_kind = "contents")

**Назначение:** Детекция оглавлений (table of contents) и другого front-matter, который не имеет PRIMARY SIGNAL typography.

**Bounded front-matter window concept:**

Contents sections физически расположены в начале выпуска (архитектурный инвариант журналов). BoundaryDetector использует **bounded front-matter window** для детекции Contents — ограниченное окно поиска на первых страницах, а не сканирование всего выпуска.

**Detection method:**
1. Сканировать anchors для `type == "contents_marker"` на первых страницах выпуска.
2. Если marker найден в пределах bounded window → классифицировать как Contents.
3. Contents range расширяется от page 1 до page перед первой non-contents статьёй.

**Signals object для Contents:**
```json
{
  "primary": "contents_marker_on_first_pages",
  "detection_method": "special_case_front_matter"
}
```

**Temporary heuristic (bounded front-matter window):**

Текущая реализация для некоторых RU-журналов использует bounded front-matter window с эмпирически выбранным верхним ограничением страниц (`max_page`) для детекции Contents. Этот параметр **journal-dependent** (зависит от журнала) и **non-invariant** (не является универсальной константой).

- **Для Mg_2025-12:** Empirical observation показывает Contents на pages 1-4.
- **Для других журналов:** Может быть 2 pages, 5 pages, 6+ pages в зависимости от издания.
- **Конкретное numeric value НЕ является verifiable constant** и может меняться per-journal/per-issue.

Дизайн BoundaryDetector фиксирует **принцип bounded front-matter window**, но не фиксирует конкретное numeric значение `max_page` как глобальное правило.

**Future refinement:**
- Per-journal configuration (`journal_code` → `max_page` mapping).
- Layout-based detection (автоматическое определение front-matter boundary).
- Journal metadata integration.

**Implementation:** Функция `_detect_contents_on_first_pages(anchors, max_page)` в `agents/boundary_detector/detector.py`. Параметр `max_page` передаётся как аргумент, не hardcoded constant.

---

#### 3.6.2 Editorial (material_kind = "editorial")

**Назначение:** Детекция редакционных материалов (editorial, foreword, preface), которые не содержат извлекаемых авторов исследовательских статей.

**Classification rule:**

Article start классифицируется как **Editorial**, если:
- PRIMARY SIGNAL (typography) обнаружен на page N,
- **НЕТ** извлекаемых авторов на page N (window=0).

**Window logic:**
- **Editorial detection:** window=0 (только текущая страница)
- **Research detection:** window=1 (текущая + следующая страница для билингвальных layout)

**Rationale:** В билингвальных выпусках Editorial часто предшествует Research article на следующей странице. Использование window=1 для editorial ошибочно захватит авторов с page N+1 и классифицирует Editorial как Research.

**Editorial greeting filter:**

Editorial pages могут содержать text blocks, ошибочно классифицированные как `ru_authors` MetadataExtractor'ом (например, приветственные обращения редакции). BoundaryDetector применяет **post-processing filter** для исключения таких случаев.

**Patterns filtered:**
- Greeting phrases: "Уважаемые", "С уважением", "Дорогие", "коллеги", "читатели"
- Academic titles: "доктор медицинских наук", "профессор кафедры", "заведующая лабораторией"
- Long text (>200 chars) с institutional affiliations
- Exclamation endings с addressing words: "коллеги!", "читатели!"

**Implementation:** Функция `_is_editorial_greeting()` в `agents/boundary_detector/detector.py`.

**Temporary heuristic (Editorial greeting filter):**

Паттерны приветствий и подписей выведены из конкретных выпусков, включая Mg_2025-12, и обеспечивают **incomplete coverage** по дизайну.

- **Journal-specific:** Greeting conventions варьируются по культуре журналов (RU vs EN, academic vs popular science).
- **Incomplete by design:** Pattern list не претендует на исчерпывающее покрытие всех возможных Editorial formats.
- **Expected extension:** Список паттернов будет расширяться по мере обнаружения новых Editorial greeting conventions в других журналах.

**Architectural note:**

Идеальное решение — улучшить MetadataExtractor для корректного разделения `ru_title` / `ru_authors` / editorial text. Текущий фильтр — **defensive programming** для обработки upstream edge cases.

**Downstream:**

BoundaryDetector только классифицирует material_kind и задаёт границы. Генерация filename для Editorial (`{IssuePrefix}_{PPP-PPP}_Editorial.pdf`) выполняется **MetadataVerifier + FilenameGenerationPolicy v_1_0**.

---

#### 3.6.3 Research / Digest (material_kind = "research", "digest")

**Research (material_kind = "research"):**

Article start классифицируется как **Research**, если:
- PRIMARY SIGNAL (typography) обнаружен на page N,
- **ЕСТЬ** извлекаемые авторы (`ru_authors` или `en_authors`) в window [page N, page N+1].

**Window logic:**
- window=1 поддерживает билингвальный layout: RU-authors на page N, EN-authors на page N+1.
- Editorial greeting filter применяется для исключения ложных `ru_authors` (см. §3.6.2).

**Downstream:**

BoundaryDetector только классифицирует material_kind и задаёт границы. Генерация filename для Research articles (`{IssuePrefix}_{PPP-PPP}_{FirstAuthorSurname}.pdf`) выполняется **MetadataVerifier + FilenameGenerationPolicy v_1_0**:
- Извлечение first author surname из anchors (`ru_authors` → transliteration, `en_authors` → validation).
- Защита от gene symbols (TPM1, LPL) и rsID patterns (rs1143634).

**Digest (material_kind = "digest"):**

Зарезервировано для digest/summary materials (journal-specific logic).

- Если реализация уже различает digest-like materials, они классифицируются как `material_kind = "digest"`.
- Если логика частичная или неполная, это будет расширено в будущих версиях.

---

#### 3.6.4 Info (material_kind = "info") ⭐ NEW in v_1_3

**Назначение:** Детекция редакционных информационных разделов («Единые требования к рукописям», «Информация для авторов», объявления журнала).

**Classification rule:**

Article start классифицируется как **Info**, если функция `_is_info_section_page(page)` возвращает True:
- На странице присутствует standalone «ИНФОРМАЦИЯ» / «INFORMATION» `text_block`,
- **И** на странице **отсутствует** article-level DOI.

**Семантика (критически важно):**

| Условие | material_kind |
|---------|---------------|
| «ИНФОРМАЦИЯ» text_block + DOI присутствует | `research` (рубрика журнала) |
| «ИНФОРМАЦИЯ» text_block + DOI отсутствует | `info` (раздел журнала) |

В журнале Mh рубрика «ИНФОРМАЦИЯ» встречается как заголовок research-статьи (имеет DOI) **и** как заголовок редакционного info-раздела (без DOI). DOI является надёжным разделителем этих случаев.

**Implementation:** Функция `_is_info_section_page(page, page_anchors)` в `agents/boundary_detector/detector.py` v1.3.1.

**Signals object для Info:**
```json
{
  "primary": "info_section_page",
  "detection_method": "info_text_block_no_doi"
}
```

**Downstream:**

BoundaryDetector классифицирует material_kind = "info" и задаёт границы. Генерация filename (`{IssuePrefix}_{PPP-PPP}_Info.pdf`) выполняется **MetadataVerifier + FilenameGenerationPolicy v_1_2**.

**Validation:**
- Mh_2026-02: pages 68-78, `Mh_2026-02_068-078_Info.pdf`
- Верификация: `ls /srv/pdf-extractor/exports/Mh/2026/Mh_2026-02/exports/2026_02_21__19_04_46/articles/ | grep Info`

**Material kind values:**

Значения `material_kind` должны точно совпадать с теми, что используются в implementation (`agents/boundary_detector/detector.py`) и TechSpec v_2_7 §7.4.1:
- `"contents"` — front matter (table of contents)
- `"editorial"` — editorial/foreword materials
- `"research"` — research articles
- `"digest"` — digest/summary materials (если реализовано)
- `"info"` — editorial guidelines / journal announcements (NEW)

---

## 4. Golden-test protocol (референсный PDF)

### 4.1 Цель golden-test

Подтвердить, что BoundaryDetector v_1_1:
- корректно находит начала статей в референсном выпуске (typography-based),
- не срабатывает на blacklist паттернах (номера выпусков, рубрики),
- корректно фильтрует RU/EN duplicates (bilingual layout),
- воспроизводимо выдаёт один и тот же результат при повторных запусках.

---

### 4.2 Входные данные golden-test

- Референсный PDF: `Mg_2025-12.pdf`
- Anchors JSON из MetadataExtractor (как есть, без фильтрации).

---

### 4.3 Процедура golden-test (детерминированная)

#### Шаг 1. Получить anchors JSON
- Запустить MetadataExtractor на референсном PDF.
- Сохранить полный JSON-вывод (stdout) как артефакт теста.

#### Шаг 2. Запустить BoundaryDetector
- Передать anchors JSON в BoundaryDetector.
- Сохранить JSON-вывод как артефакт теста.

#### Шаг 3. Проверить инварианты (см. 4.4)
- Проверки выполняются на структуре JSON, без ручной интерпретации.

#### Шаг 4. Зафиксировать golden outputs
- `anchors_golden.json`
- `boundaries_golden.json`
- (опционально) `boundaries_summary.md` — человекочитаемый отчёт (генерируется из JSON).

---

### 4.4 Инварианты, которые обязаны выполняться

#### I1. Детерминизм
Повторный запуск на тех же входных данных выдаёт:
- идентичный `article_starts[]` (страницы и порядок)
- идентичные `signals` (структурно и по значениям)
- идентичные `confidence` (с точностью до фиксированного округления, если округление применяется)

#### I2. Валидация диапазонов
- каждый `start_page` ∈ [1, total_pages]
- start_page уникальны
- start_page строго возрастают

#### I3. Политика typography-based detection
Для каждой найденной статьи:
- `signals.primary == "typography_descriptor"`
- `signals.font_name` присутствует и не пустой
- `signals.font_size` присутствует и соответствует ожидаемому диапазону (tolerance учтён)
- `signals.blacklist` присутствует (может быть пустым массивом)
- `signals.ru_en_dedup_policy` указывает статус политики дедупликации (enabled/disabled)

#### I4. Фиксированная confidence
Все start_page в результате:
- имеют `confidence == 1.0` (фиксированное значение, не вычисляемый score)

---

## 5. Границы ответственности

BoundaryDetector v_1_3:
- ✅ реализует ArticleStartPolicy v_1_0
- ✅ классифицирует тип материала (material_kind: contents/editorial/research/digest/info)
- ✅ формирует только границы (start pages)
- ✅ сохраняет аудит signals

BoundaryDetector v_1_3 не делает:
- ❌ разрезание PDF
- ❌ извлечение текста «с нуля»
- ❌ нормализацию/очистку anchors на входе (кроме структурирования per-page)
- ❌ генерацию filename (это MetadataVerifier + FilenameGenerationPolicy v_1_2)
- ❌ извлечение author surnames (это MetadataVerifier)

---

## 6. Версионирование и изменения

Документ **BoundaryDetector v_1_3** является каноническим.

**Предыдущая версия:** BoundaryDetector v_1_2

### Изменения в v_1_3 (2026-02-21)

**Цель:** Документировать `info` material_kind, добавленный в detector.py v1.3.1 для журнала Mh.

**Изменения:**

1. **§1 Цель компонента:** Добавлен `info` в список material_kinds.

2. **§2.2.1 Поля результата:** Добавлено `"info"` в enum material_kind.

3. **§3.6.4 Info (NEW):**
   - Задокументирован `_is_info_section_page()`: standalone ИНФОРМАЦИЯ/INFORMATION text_block + нет DOI
   - Задокументирована семантика: рубрика с DOI (research) vs раздел без DOI (info)
   - Signals object для info
   - Validation: Mh_2026-02 (pages 68-78)

4. **§5 Границы ответственности:** Обновлены списки материалов.

5. **Cross-references:** TechSpec v_2_7, FilenameGenerationPolicy v_1_2.

**Compatibility:** Additive change. Consumers с `material_kind` enum validation должны добавить `"info"`.

**Validation:**
- Mh_2026-02: T=L=E=9, sha256 verified (2026-02-21)
- Export: `/srv/pdf-extractor/exports/Mh/2026/Mh_2026-02/exports/2026_02_21__19_04_46/`

---

### Изменения в v_1_1 (2026-01-22)

**Цель:** Минимальный patch-diff для приведения в соответствие с TechSpec v_2_5 и реализацией typography-based detection.

**Изменения:**
1. **§2.2 Output Schema:** Заменён формат `article_starts` на rich objects с полями `start_page`, `confidence`, `signals` (вместо простых integer массивов)
2. **§2.2.2:** Добавлена схема `boundary_ranges` с инвариантами (1-indexed, contiguous, non-overlapping)
3. **§3 Algorithm:** Переименован метод на "Typography-based Article Start Detection"
4. **§3.2 Candidate Generation:** PRIMARY SIGNAL заменён на typography descriptor (font_name, font_size, tolerance) вместо DOI/RU-structure
5. **§3.2 Filters:** Добавлены Filter 1 (Blacklist) и Filter 2 (RU/EN Deduplication)
6. **§3.3 Confidence:** Изменена с probabilistic scoring (base 0.50 + bonuses/penalties) на fixed 1.0 (binary match)
7. **§3.3.1-3.3.2:** Удалены секции RU-blocks detection rules (не используются в typography-based методе)
8. **§3.3.3:** Добавлено явное указание: "DOI **никогда** не используется как recognition signal"
9. **§3.4:** Обновлена логика генерации boundary_ranges с инвариантами
10. **§4.4 Invariants:** I3 изменён с RU-blocks validation на typography signals validation; I4-I6 (DOI-related) удалены; I7 изменён с `confidence >= 0.70` на `confidence == 1.0`

**Compatibility:** Выходной контракт изменён (breaking change). Consumers должны ожидать rich objects вместо integer arrays.

---

### Изменения в v_1_2 (2026-01-27)

**Цель:** Документировать material_kind и обработку front-matter / service materials, синхронизировать дизайн BoundaryDetector с TechSpec v_2_6 §7.4.1 и FilenameGenerationPolicy v_1_0.

**Изменения:**

1. **§1 Цель компонента:** Добавлено material classification в описание BoundaryDetector v_1_2.

2. **§2.2.1 Поля результата:** Добавлено поле `material_kind`:
   - В `article_starts`: классификация каждого article start.
   - В `boundary_ranges`: материал для каждого диапазона.
   - Значения: `"contents"`, `"editorial"`, `"research"`, `"digest"` (если реализовано).

3. **§3 Algorithm Title:** Переименован на "Typography-based + Material Classification".

4. **§3.6 Material Classification and Front-Matter Handling (NEW):**

   **§3.6.1 Contents (material_kind = "contents"):**
   - Документирован **bounded front-matter window** для Contents detection как journal-dependent, non-invariant эвристика.
   - Конкретные numeric значения `max_page` НЕ фиксированы как глобальный инвариант.
   - Mg_2025-12: empirical observation (Contents на pages 1-4).
   - Другие журналы: может быть 2, 5, 6+ pages в зависимости от издания.
   - Дизайн фиксирует **принцип bounded window**, не конкретное число.
   - **Temporary heuristic** явно помечена.

   **§3.6.2 Editorial (material_kind = "editorial"):**
   - Документирован **greeting filter** для Editorial materials.
   - Паттерны приветствий ("Уважаемые", "С уважением", academic titles) выведены из Mg_2025-12.
   - **Incomplete coverage** явно отмечено: pattern list не претендует на исчерпывающее покрытие.
   - **Temporary heuristic** явно помечена.
   - Документирован **window logic**: window=0 для editorial, window=1 для research.

   **§3.6.3 Research / Digest:**
   - Research: статьи с извлекаемыми авторами (window=1 для билингвального layout).
   - Digest: зарезервировано для journal-specific logic (если реализовано).
   - Уточнено, что filename-логика для Research живёт в MetadataVerifier + FilenameGenerationPolicy v_1_0.

5. **§5 Границы ответственности:** Добавлена material classification в список ответственностей BoundaryDetector v_1_2. Уточнено, что BoundaryDetector только классифицирует и задаёт границы; filename-логика реализована в MetadataVerifier + FilenameGenerationPolicy v_1_0.

6. **Cross-references:** Добавлены ссылки на:
   - TechSpec v_2_6 §7.4.1 (Material Classification rules).
   - FilenameGenerationPolicy v_1_0 (usage of material_kind в filenames).
   - Implementation: `agents/boundary_detector/detector.py` v1.2.0.

**Temporary Heuristics (explicit labels):**
- **Bounded front-matter window** (`max_page`) для Contents detection: journal-dependent, non-invariant numeric value.
- **Editorial greeting filter patterns**: Mg_2025-12 derived, incomplete coverage по дизайну.
- **Window logic** (window=0 для editorial vs window=1 для research): fix for consecutive article false positives.

**Implementation Reference:**
- BoundaryDetector v1.1.0 → v1.2.0
- Commit: `b9f215d` — feat(material): implement RU-journal filename policy and fix classification issues

**Compatibility:**
- Output contract extended (additive change).
- `material_kind` field required в downstream consumers (MetadataVerifier, OutputBuilder).
- Backwards-compatible с v_1_1 if consumers ignore `material_kind` field.

**Validation:**
- Golden test: Mg_2025-12 (29 articles: 1 Contents, 1 Editorial, 27 Research)
- Result: EXACT MATCH на всех material classifications

---

Любое дальнейшее изменение:
- только через выпуск новой версии (v_1_3+),
- только как минимальный patch-diff,
- только после явного подтверждения.

