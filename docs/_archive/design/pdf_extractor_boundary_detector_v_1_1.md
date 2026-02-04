# PDF Extractor — BoundaryDetector v_1_1

**Project:** PDF Extractor
**Phase:** 2.4 BoundaryDetector
**Status:** Canonical
**Version:** v_1_1
**Depends on:** PDF Extractor — ArticleStartPolicy v_1_0
**Previous version:** v_1_0

---

## 1. Цель компонента

BoundaryDetector v_1_1 — детерминированный компонент, который принимает **сырые anchors** (наблюдаемые факты из PDF) и применяет **ArticleStartPolicy v_1_0** для определения:

- страниц начала каждой статьи (article start pages),
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
  - `signals` (dict): детерминированные сигналы обнаружения (policy constants):
    - `primary`: метод детекции (`"typography_descriptor"`).
    - `font_name`, `font_size`, `tolerance`: параметры типографики из ArticleStartPolicy v_1_0.
    - `blacklist`: список запрещённых паттернов (из policy).
    - `ru_en_dedup_policy`: `"enabled"` | `"disabled"` (из policy.duplicate_filter_enabled).
- `boundary_ranges` (array): диапазоны для Splitter (сгенерированы из article_starts).
  - `id` (str): идентификатор статьи (a01, a02, ...).
  - `from` (int): начало диапазона (1-indexed, совпадает с start_page).
  - `to` (int): конец диапазона (1-indexed, inclusive).
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

## 3. Детерминированный алгоритм BoundaryDetector v_1_1 (Typography-based)

Алгоритм основан на ArticleStartPolicy v_1_0 (Typography-based) и состоит из трёх стадий:

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

BoundaryDetector v_1_1:
- ✅ реализует ArticleStartPolicy v_1_0
- ✅ формирует только границы (start pages)
- ✅ сохраняет аудит signals

BoundaryDetector v_1_0 не делает:
- ❌ разрезание PDF
- ❌ извлечение текста «с нуля»
- ❌ нормализацию/очистку anchors на входе (кроме структурирования per-page)

---

## 6. Версионирование и изменения

Документ **BoundaryDetector v_1_1** является каноническим.

**Предыдущая версия:** [BoundaryDetector v_1_0](../_archive/design/pdf_extractor_boundary_detector_v_1_0.md)

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

Любое дальнейшее изменение:
- только через выпуск новой версии (v_1_2+),
- только как минимальный patch-diff,
- только после явного подтверждения.

