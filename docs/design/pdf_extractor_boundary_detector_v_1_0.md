# PDF Extractor — BoundaryDetector v_1_0

**Project:** PDF Extractor  
**Phase:** 2.4 BoundaryDetector  
**Status:** Canonical  
**Version:** v_1_0  
**Depends on:** PDF Extractor — ArticleStartPolicy v_1_0  

---

## 1. Цель компонента

BoundaryDetector v_1_0 — детерминированный компонент, который принимает **сырые anchors** (наблюдаемые факты из PDF) и применяет **ArticleStartPolicy v_1_0** для определения:

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

#### 2.2.1 Поля результата

- `article_starts` (array): список найденных начал статей.
- `start_page` (int): номер страницы начала статьи (1-based).
- `confidence` (float 0..1): итоговая уверенность.
- `signals` (object): аудит-структура, содержащая:
  - булевы флаги обязательных RU-блоков,
  - опциональные блоки,
  - информацию о DOI,
  - результат проверки constraints,
  - список anti-signals.

#### 2.2.2 Гарантии

- `article_starts` отсортирован по `start_page` по возрастанию.
- Значения `start_page` уникальны.
- Первая найденная статья не может иметь `start_page < 1` или `> total_pages`.

---

## 3. Детерминированный алгоритм BoundaryDetector v_1_0 (без кода)

Алгоритм состоит из трёх стадий:

1) Нормализация и группировка anchors по страницам
2) Генерация кандидатов на начало статьи (candidate pages)
3) Оценка кандидатов по ArticleStartPolicy v_1_0 (signals + constraints + anti-signals) и финальное решение

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

### 3.2 Стадия 2 — Генерация кандидатов начала статьи

BoundaryDetector v_1_0 использует **суперпозицию** источников кандидатов:

#### Источник кандидатов A: структурный DOI издательства
Страница `p` становится кандидатом, если на ней найден DOI, удовлетворяющий:
- начинается с `10.25557/`
- после слэша содержит компонент `journal_id` (например `2073-7998` или `1682-8313`)
- содержит `.<year>.<issue>.`
- содержит page-range `.<start>-<end>` в конце

Примечание: этот тест не должен привязываться к одному журналу; `journal_id` рассматривается как параметр, извлекаемый из DOI.

#### Источник кандидатов B: RU-структура начала статьи (без DOI)
Страница `p` становится кандидатом, если на ней в верхней зоне обнаружены признаки последовательности RU-блоков:
- крупный RU-заголовок (text_block на max font size)
- сразу ниже — RU-авторы (text_block на RU, меньший font size)
- далее — RU-аффилиации/адрес (text_block RU)
- далее — начало RU-аннотации (маркер "Аннотация" или текст, похожий на аннотацию)

Этот источник предназначен для случаев, когда DOI:
- отсутствует,
- повреждён,
- или не извлечён.

#### Источник кандидатов C: переходная страница (страховка)
Если кандидат не найден на странице `p`, но на `p+1` обнаружены Optional-блоки, характерные для начала статьи ("Ключевые слова", "Для цитирования", "Received/Accepted" и т.п.), то:
- `p` добавляется в кандидаты как "candidate_by_overflow".

Ограничение: источник C никогда не порождает кандидата, если на `p` нет сильных RU-признаков (заголовок/авторы/аффилиации).

---

### 3.3 Стадия 3 — Оценка кандидатов по ArticleStartPolicy v_1_0

Для каждого кандидата `p` вычисляются:

- `required_ru_blocks_score`
- `constraints_score`
- `optional_signals_score`
- `anti_signals_penalty`

Итоговая уверенность:

```
confidence = clamp( base + required + constraints + optional - penalties, 0..1 )
```

Где все компоненты детерминированы и документированы ниже.

---

#### 3.3.1 Детект required RU blocks

**Обязательные RU-блоки (все должны быть true):**

1) `ru_title`
2) `ru_authors`
3) `ru_affiliations`
4) `ru_address`
5) `ru_abstract`

##### Правило окна 1–2 страниц
Required-блоки могут быть распределены на:
- странице `p` (первая страница статьи),
- или страницах `p` и `p+1` (если EN-блоки/служебные блоки переносятся).

Гарантия v_1_0:
- `ru_title` должен быть на `p`.
- `ru_abstract` должен начинаться на `p` (маркер/текст), но может продолжаться на `p+1`.
- Optional RU blocks могут быть на `p+1`.

##### Детерминированные критерии распознавания required RU blocks

- `ru_title`:
  - language=ru
  - расположен в top_40%
  - font_size == max_font_size_on_page(p)
  - текст не похож на колонтитул (см. anti-signals)

- `ru_authors`:
  - language=ru
  - расположен ниже ru_title (по y)
  - font_size < ru_title_font_size
  - содержит паттерны имён/инициалов (эвристика допускается только через проверяемые признаки: наличие пробелов, точек, запятых; отсутствие ключевых слов "Аннотация", "Ключевые слова")

- `ru_affiliations`:
  - language=ru
  - расположен ниже authors
  - содержит типичные признаки аффилиации (например: учреждения, города; допускается словарь-триггеров уровня "университет", "институт", "центр", "клиника", "лаборатория", "г."; если словарь не используется, допускается критерий многострочного блока + наличие цифр/верхних индексов)

- `ru_address`:
  - language=ru
  - расположен рядом/после affiliations
  - содержит признаки адреса (индекс/улица/город/страна; допускаются триггеры "ул.", "просп.", "г.", "Россия"; при отсутствии словаря — наличие цифр и разделителей)

- `ru_abstract`:
  - presence of section marker "Аннотация" (или эквивалент)
  - либо наличие блока текста сразу после заголовка/аффилиаций с типичными признаками аннотации (многострочный абзац, язык=ru)

Примечание: BoundaryDetector v_1_0 в отчёте signals обязан отражать, **каким способом** был детектирован abstract: marker-based или text-based.

---

#### 3.3.2 Проверка constraints

Constraints из ArticleStartPolicy v_1_0:

- `page_position_top_40`: ru_title находится в top_40%
- `ru_title_max_font_on_page`: ru_title имеет максимальный font_size
- `canonical_sequence_ru`: порядок RU-блоков соответствует канону (title → authors → affiliations/address → abstract)

Каждый constraint даёт детерминированный вклад в confidence.

---

#### 3.3.3 Optional signals (усиливающие)

Optional RU blocks (каждый найденный блок увеличивает confidence, но не делает статью валидной сам по себе):

- `keywords_ru` ("Ключевые слова")
- `for_citation_ru` ("Для цитирования")
- `service_blocks_ru` ("Автор для корреспонденции", "Финансирование", "Конфликт интересов", "Поступила", "Принята")

Optional EN block:

- `en_block_present` становится true, если обнаружена последовательность EN-секций или маркеров в пределах `p` и/или `p+1`.

---

#### 3.3.4 DOI handling (строго по политике)

BoundaryDetector v_1_0 **не доверяет** любому DOI.

Правила:

1) DOI считается кандидатом `doi_publisher_structured`, если:
   - соответствует структурному шаблону издательства (см. 3.2.A)
   - и расположен в верхней части страницы `p` (не в нижнем списке)

2) Если на странице `p` есть несколько DOI:
   - приоритет отдаётся `doi_publisher_structured`
   - остальные DOI считаются шумом (включая References DOI) и отражаются в signals как `other_dois_on_page_count`

3) DOI из References не должен порождать границу:
   - если DOI расположен в нижней/средней зоне,
   - и отсутствуют required RU blocks,
   - то это anti-signal.

---

#### 3.3.5 Anti-signals (штрафы)

Список anti-signals формируется для каждой страницы `p`:

- `doi_cluster_like_references`:
  - много DOI на странице (выше порога)
  - и они равномерно распределены по странице

- `doi_in_bottom_zone`:
  - DOI найден, но bbox в нижней зоне

- `header_footer_repetition`:
  - один и тот же DOI повторяется на множестве нечётных страниц
  - и расположен в узкой верхней полосе (подозрение на колонтитул)

- `missing_required_ru_blocks`

Anti-signals не запрещают candidate автоматически, но снижают confidence.

---

### 3.4 Агрегация сигналов в confidence (детерминированная шкала)

BoundaryDetector v_1_0 использует фиксированную шкалу (может быть изменена только через v_1_1+).

#### 3.4.1 Базовый уровень
- `base = 0.50` для страницы-кандидата.

#### 3.4.2 Required RU blocks
Если все required RU blocks подтверждены (в окне p..p+1):
- `required_bonus = +0.30`
Иначе:
- candidate отклоняется (страница не может быть start_page).

#### 3.4.3 Constraints
- `page_position_top_40` = +0.05
- `ru_title_max_font_on_page` = +0.05
- `canonical_sequence_ru` = +0.05

#### 3.4.4 Optional signals
- `doi_publisher_structured` = +0.05
- каждый из optional RU blocks (keywords_ru, for_citation_ru, service_blocks_ru) = +0.02 (суммарно максимум +0.06)
- `en_block_present` = +0.03

#### 3.4.5 Penalties (anti-signals)
- `doi_cluster_like_references` = -0.10
- `doi_in_bottom_zone` = -0.10
- `header_footer_repetition` = -0.10
- другие anti-signals (если появятся в v_1_1+) — только через версионирование.

#### 3.4.6 Порог принятия
Страница признаётся началом статьи, если:
- required RU blocks = true
- `confidence >= 0.70`

---

### 3.5 Финальная консолидация article_starts

После вычисления всех кандидатов:

1) Отсортировать по `start_page`.
2) Удалить дубликаты (если один и тот же start_page найден несколькими источниками кандидатов) — оставить запись с максимальной confidence и объединёнными signals.
3) Проверить монотонность: start_page строго возрастают.
4) Проверить, что расстояние между соседними start_page не нарушает физическую структуру (не может быть 2 старта на одной и той же странице; допускается старт на соседних страницах только если policy допускает «статья на 1 странице», но тогда required blocks должны подтверждаться).

---

## 4. Golden-test protocol (референсный PDF)

### 4.1 Цель golden-test

Подтвердить, что BoundaryDetector v_1_0:
- корректно находит начала статей в референсном выпуске,
- не срабатывает на DOI в колонтитулах и References,
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

#### I3. Политика required RU blocks
Для каждой найденной статьи:
- `signals.ru_title == true`
- `signals.ru_authors == true`
- `signals.ru_affiliations == true`
- `signals.ru_address == true`
- `signals.ru_abstract == true`

#### I4. DOI не является единственным фактором
Для каждой найденной статьи:
- даже если `doi_publisher_structured == true`, required RU blocks обязаны быть true.

#### I5. Защита от References DOI
Страницы, на которых много DOI (cluster), не должны становиться start_page, если:
- отсутствуют required RU blocks.

#### I6. Защита от колонтитулов
Повторяющийся DOI в верхней узкой полосе на нечётных страницах:
- не должен создавать start_page
- должен отражаться как anti-signal `header_footer_repetition`, если он участвует в оценке кандидата.

#### I7. Порог принятия
Все start_page в результате:
- имеют `confidence >= 0.70`

---

## 5. Границы ответственности

BoundaryDetector v_1_0:
- ✅ реализует ArticleStartPolicy v_1_0
- ✅ формирует только границы (start pages)
- ✅ сохраняет аудит signals

BoundaryDetector v_1_0 не делает:
- ❌ разрезание PDF
- ❌ извлечение текста «с нуля»
- ❌ нормализацию/очистку anchors на входе (кроме структурирования per-page)

---

## 6. Версионирование и изменения

Документ **BoundaryDetector v_1_0** является каноническим.

Любое изменение:
- только через выпуск новой версии (v_1_1+),
- только как минимальный patch-diff,
- только после явного подтверждения.

