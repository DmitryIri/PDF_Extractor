# Filename Generation Policy v_1_2

**Статус:** Canonical
**Проект:** PDF Extractor
**Область применения:** формирование имён файлов для статей из RU-журналов
**Дата:** 2026-02-21
**Предыдущая версия:** v_1_1

---

## 1. Назначение документа

Данный документ фиксирует **детерминированную и проверенную политику формирования имён файлов** для отдельных статей, извлечённых из PDF-выпусков научных журналов с русскоязычными метаданными (RU-журналы).

Политика является **нормативной** и используется компонентами пайплайна:
- **MetadataVerifier** — извлечение фамилии первого автора и формирование `expected_filename`
- **OutputBuilder** — создание файлов с каноническими именами

Документ определяет:
- Канонический формат имени файла
- Приоритет источников метаданных (RU vs EN)
- Правила транслитерации
- Валидацию против gene/rsID паттернов
- Обработку специальных материалов (Contents, Editorial, Digest)

---

## 2. Базовый принцип

**Имя файла статьи формируется детерминированно из метаданных, извлечённых на этапе MetadataExtractor.**

Политика различает:
- **Research articles** — научные статьи с извлекаемыми авторами
- **Service materials** — Contents, Editorial, Digest (без авторов)

---

## 3. Канонический формат имени файла

### 3.1 Research articles

```
{IssuePrefix}_{PPP-PPP}_{FirstAuthorSurname}.pdf
```

**Компоненты:**
- `{IssuePrefix}` — префикс выпуска (например, `Mg_2025-12`)
- `{PPP-PPP}` — диапазон страниц (3-digit zero-padded, inclusive)
- `{FirstAuthorSurname}` — фамилия первого автора (латиница, capitalized)

**Примеры:**
```
Mg_2025-12_016-027_Burykina.pdf
Mg_2025-12_067-073_Zaklyazminskaya.pdf
Mg_2025-12_110-112_Bragina.pdf
```

### 3.2 Service materials

```
{IssuePrefix}_{PPP-PPP}_{ServiceSuffix}.pdf
```

**Service suffixes:**
- `Contents` — table of contents
- `Editorial` — editorial/foreword
- `Digest` — digest/summary materials
- `Info` — editorial guidelines / journal announcements (**NEW in v_1_2**)

**Примеры:**
```
Mg_2025-12_001-004_Contents.pdf
Mg_2025-12_005-005_Editorial.pdf
Mg_2025-12_074-080_Digest.pdf
Mh_2026-02_068-078_Info.pdf
```

---

## 4. Извлечение фамилии первого автора (Research articles)

### 4.1 Приоритет источников (RU-журналы)

Алгоритм извлечения фамилии выполняется в четыре шага (STEP A → B → C → D):

**STEP A — ru_authors + en_authors** (с фильтром running-header):
- `ru_anchor` = первый NON-HEADER `ru_authors` в окне `[from_page, from_page+1]`
- Если найден: извлечённая фамилия транслитерируется (GOST); параллельно проверяется `en_authors` как авторская транслитерация
- Source: `ru_authors_author_translit` или `ru_authors_translit`

**STEP B — en_authors only** (если STEP A не дал результата):
- `en_anchor` = первый NON-HEADER `en_authors` в окне
- Source: `en_authors`

**STEP C — text_block fallback** (если STEP A и B не дали результата):
- Сканирует первые N=6 `text_block` anchors в окне
- Требует: 2-initial byline pattern (`Surname I.I.`)
- Предпочтение RU-кандидату (GOST транслитерация детерминистична)
- Source: `text_block_translit` (RU→GOST) или `text_block` (EN)

**STEP D — deferred** (не реализован в текущей версии):
- Заблокирован ограничением OutputValidator: regex фамилии `[A-Z][a-z]+` отвергает цифры
- Пока в силе exit-40 при невозможности извлечь фамилию

### 4.2 Извлечение фамилии из ru_authors

**Формат:** `Фамилия И.О.` или `Фамилия И.О., Фамилия И.О., ...`

**Алгоритм:**
1. Split по запятой (`,`)
2. Взять первый элемент
3. Split по пробелу
4. Взять первое слово (фамилия)

**Пример:**
```
ru_authors: "Брагина Е.Ю., Фрейдин М.Б."
→ Surname: "Брагина"
```

### 4.3 Транслитерация (GOST 7.79-2000 System B)

**Иерархия транслитерации:**
1. **Авторская транслитерация** (preferred):
   - Если en_authors доступен на той же странице (или page+1)
   - И извлечённая фамилия проходит валидацию (§4.5)
   - Используется фамилия из en_authors напрямую
   - **Source:** `ru_authors_author_translit`

2. **GOST механическая транслитерация** (fallback):
   - Применяется GOST 7.79-2000 System B к русской фамилии
   - **Контекстные правила** (для улучшения читаемости):
     - Rule 1: `ие` → `iye` (Муртазалиева → Murtazaliyeva)
     - Rule 2: `ню` → `niu` (Гуменюк → Gumeniuk)
     - Rule 3: word-final `ый` → `yi` (Безчасный → Bezchasnyi) — **NEW in v_1_1**
   - **Source:** `ru_authors_translit`

**Rule 3 детали:**
- Срабатывает только на слово-конечном `й` после `ы`
- «Слово-конечный» = последний символ строки ИЛИ следующий символ не кириллица
- Не влияет на: `ой` (Горовой → Gorovoy), `ей`, `ай`, `ий`
- Не влияет на `ый` внутри слова (например, «Выйти» — й после ы, но не в конце слова → стандартное `yy`)

**Примеры:**
```
Брагина           → Bragina
Муртазалиева      → Murtazaliyeva  (rule 1: ие→iye)
Гуменюк           → Gumeniuk       (rule 2: ню→niu)
Безчасный         → Bezchasnyi     (rule 3: ый→yi)  [NEW]
Горовой           → Gorovoy        (rule 3 not triggered: й after о)
```

### 4.4 Извлечение фамилии из en_authors

**Формат:** `Surname I.I.` или `Surname I.I., Surname I.I., ...`

**Алгоритм:**
1. Split по запятой (`,`)
2. Взять первый элемент
3. Split по пробелу
4. Взять первое слово (фамилия)

**Пример:**
```
en_authors: "Gandaeva M.S., Korobova Z.R."
→ Surname: "Gandaeva"
```

### 4.5 Валидация фамилии (en_authors)

**Цель:** исключить использование gene symbols и rsID в качестве фамилий.

**Reject patterns:**
- rsID: `^rs\d+` (например, rs1143634)
- Biological notation: содержит `(` или `)`
- Digits: содержит цифры
- All-caps short words: все заглавные AND длина ≤ 8 (TPM1, TGFBR1, MMP1, LPL, LMF1)

**Accept patterns:**
- Capitalized word: `^[A-Z][a-z]` (Gandaeva, Burykina, Zaklyazminskaya)
- Mixed case с lowercase letters

### 4.6 STEP C: text_block fallback (NEW in v_1_1)

Когда STEP A и B не возвращают валидную фамилию (ru_authors / en_authors отсутствуют или содержат только running headers), поиск продолжается в `text_block` anchors.

**Алгоритм:**
1. Сканировать `text_block` anchors в окне `[from_page, from_page+1]` в порядке anchor-list. N=6 — бюджет кандидатов: только text_block, прошедших byline-filter, считаются против лимита. Running headers и non-byline blocks (page numbers, section titles) прозрачны для счётчика.
2. Для каждого text_block:
   - Skip если `is_running_header(text)` → True
   - Skip если NOT `looks_like_author_byline(text)` (2-initial pattern: `Surname I.I.`)
   - Извлечь первое слово как кандидата фамилии
3. Собрать два кандидата (первый валидный каждого типа):
   - `ru_candidate`: если кандидат начинается с кириллицы → GOST транслитерация → `is_valid_surname(…, step_c=True)`
   - `en_candidate`: если латиница → `_capitalize_surname` + `_validate_surname_en` + `is_valid_surname(…, step_c=True)`
4. Предпочтение: `ru_candidate` (GOST детерминистичен); `en_candidate` как fallback

**Byline regex (2 initials):**
```
^[Surname]+[\s,]+[Initial].\s*[Initial].
```
Требование 2 инициалов позволяет структурно отличить byline от однобуквенных меток («Table A.», «Note C.»).

**Stopword контракт в STEP C:**
- HARD stopwords (`Vol`, `Tom`, `Contents`, `Editorial`, `Digest`) — отклоняются
- SOFT stopwords (`Table`, `Fig`, `Note`, …) — отклоняются только в контексте STEP C

---

## 5. Window для поиска anchors

**Определение:** window — диапазон страниц для поиска метаданных относительно начала статьи.

**Правила:**
- **ru_authors:** `[from_page, from_page+1]` (текущая страница + следующая)
- **en_authors:** `[from_page, from_page+1]` (текущая страница + следующая)
- **text_block** (STEP C): `[from_page, from_page+1]` — тот же окон; N=6 считает только byline-pattern кандидаты (running headers и non-byline blocks прозрачны для счётчика)

**Обоснование:** в билингвальных выпусках RU-метаданные на странице N, EN-метаданные на странице N+1.  text_block bylines расположены на той же странице что и другие метаданные.

---

## 6. Определение material_kind

**Material classification** выполняется компонентом **BoundaryDetector**.

**Типы:**
- `contents` — table of contents (multi-page)
- `editorial` — editorial/foreword (без извлекаемых авторов)
- `research` — research article (с извлекаемыми авторами)
- `digest` — digest/summary materials (journal-specific)
- `info` — editorial guidelines / journal announcements (**NEW in v_1_2**)

**Правила:**
- Если `material_kind == "contents"` → suffix `_Contents.pdf`
- Если `material_kind == "editorial"` → suffix `_Editorial.pdf`
- Если `material_kind == "digest"` → suffix `_Digest.pdf`
- Если `material_kind == "info"` → suffix `_Info.pdf` (**NEW in v_1_2**)
- Если `material_kind == "research"` → suffix `_{FirstAuthorSurname}.pdf`

**Условие детекции `info` (BoundaryDetector):**
- Standalone «ИНФОРМАЦИЯ» / «INFORMATION» text_block на странице **И** нет article-level DOI на этой странице.
- Семантика: рубрика «ИНФОРМАЦИЯ» у research-статьи (с DOI) ≠ заголовок info-раздела (без DOI).
- Верификация: `grep "_is_info_section_page" agents/boundary_detector/detector.py`

**TOC re-verification (NEW in v_1_1):**
BoundaryDetector может «утечь» классификацию `contents` на соседние статьи (window=2 вокруг contents_marker). MetadataVerifier **повторно проверяет** перед генерацией filename:
- `effective_kind = "contents"` только если содержит `contents_marker` anchor **внутри собственного** диапазона `[from_page, to_page]`
- Иначе: `effective_kind = "research"`, `original_material_kind = "contents"` сохраняется для аудита
- Нет page_range-хардкодов: проверка опирается исключительно на данные anchors

**Детерминизм:** material_kind определяется BoundaryDetector на основе anchors (см. BoundaryDetector design v_1_2).

---

## 7. Evidence tracking

**Цель:** аудитопригодность и отладка.

**Поля в выходе MetadataVerifier:**
- `first_author_surname` (str): извлечённая фамилия (латиница)
- `first_author_surname_source` (str): источник фамилии
  - `ru_authors_author_translit` — авторская транслитерация из en_authors
  - `ru_authors_translit` — GOST механическая транслитерация
  - `en_authors` — EN-only fallback (валидирована)
  - `text_block_translit` — из text_block, RU→GOST транслитерация **[NEW]**
  - `text_block` — из text_block, EN (валидирована) **[NEW]**
- `evidence` (dict): детали обнаружения
  - `anchor_type` (str): `ru_authors`, `en_authors`, или `text_block` **[NEW]**
  - `anchor_page` (int): страница anchor
  - `en_authors_verified` (bool): была ли проверена EN фамилия (только для `ru_authors_author_translit`)
  - `text_block_index` (int): позиция в N=6 scan (только для `text_block` / `text_block_translit`) **[NEW]**

**Поля для reclassification audit:**
- `original_material_kind` (str): исходный material_kind от BoundaryDetector (присутствует только при reclassification contents→research) **[NEW]**

**Пример (research, STEP A):**
```json
{
  "first_author_surname": "Burykina",
  "first_author_surname_source": "ru_authors_author_translit",
  "evidence": {
    "anchor_type": "ru_authors",
    "anchor_page": 16,
    "en_authors_verified": true
  }
}
```

**Пример (research, STEP C):**
```json
{
  "first_author_surname": "Bezchasnyi",
  "first_author_surname_source": "text_block_translit",
  "evidence": {
    "anchor_type": "text_block",
    "anchor_page": 37,
    "text_block_index": 1
  }
}
```

---

## 8. Эмпирическая валидация

Политика валидирована на выпусках:

**Mg_2025-12 (regression baseline):**
- Журнал: «Медицинская генетика»
- Статей: **29** (1 Contents, 1 Editorial, 27 Research)
- Golden test: **EXACT MATCH** (29/29 articles)
- Gene symbols eliminated: ✅ (TPM1, LPL, rs1143634 → valid surnames)

**Mh_2026-01 (acceptance fixture for v_1_1):**
- Журнал: «Медицинская история»
- Статей: **9** (1 Contents, 8 Research)
- Целевые файлы: Contents, Roschina, Efremov, Orlov, Zhukova, Bezchasnyi, Kazakovtsev, Plotkin, Makarova

**Mh_2026-02 (acceptance fixture for v_1_2 — info material_kind):**
- Журнал: «Медицинская история»
- Статей: **9** (1 Contents, 7 Research, 1 Info)
- T=L=E=9, sha256 verified
- Целевые файлы включают: `Mh_2026-02_068-078_Info.pdf`
- Верификация: `ls /srv/pdf-extractor/exports/Mh/2026/Mh_2026-02/exports/2026_02_21__19_04_46/articles/`

**Reference:**
- Manifest: `docs/state/reference_inputs_manifest_mg_2025_12_v_1_0.json`
- Test: `tests/test_material_classification_golden.sh`

---

## 9. Ограничения и будущие улучшения

### 9.1 Текущие ограничения

- **Язык:** Политика протестирована только на RU-журналах (кириллица + латиница)
- **Транслитерация:** Контекстные правила (ие→iye, ню→niu, ый→yi) — эмпирические, не исчерпывающие
- **Gene validation:** Валидация проверяет известные паттерны; новые gene symbols могут потребовать обновления
- **STEP C scan limit:** N=6 — бюджет byline-pattern кандидатов (не всех text_blocks в окне). Running headers и non-byline blocks (page numbers, section titles, journal names) прозрачны для счётчика. Если после 6 byline-кандидатов валидная фамилия не найдена — exit-40.
- **Single-initial bylines:** Regex требует 2 initials.  Single-initial формат ("Plotkin F.") не поддерживается.  В RU-журналах этот формат не наблюдается.
- **STEP D (deterministic fallback):** Отложен. Формат «Axx» блокируется OutputValidator regex `[A-Z][a-z]+`.  Требует отдельного scope change в OutputValidator.

### 9.2 Будущие улучшения (вне текущей версии)

- Расширение поддержки на EN-журналы (EN-first, RU-optional)
- Более полный набор контекстных правил для транслитерации (например, -ский/-ская → -sky/-skaya)
- Интеграция с внешними базами gene symbols для валидации (UniProt, HGNC)
- STEP D: обновление OutputValidator regex для поддержки fallback-формата

---

## 10. Статус и правила изменения

- Документ является **каноническим источником истины** для filename generation
- Изменения допускаются **только через выпуск новой версии** (`v_1_2`, `v_2_0` и т.д.)
- Редактирование задним числом запрещено

---

## 11. CHANGELOG

- **v_1_2 — 2026-02-21** — MINOR: добавлен `info` material_kind (`_Info.pdf` suffix); задокументировано условие детекции (_is_info_section_page: standalone ИНФОРМАЦИЯ text_block + нет DOI); добавлен acceptance fixture Mh_2026-02
- **v_1_1 — 2026-02-04** — MINOR: добавлен GOST rule 3 (ый→yi); добавлен STEP C text_block fallback (source: text_block_translit / text_block); добавлена TOC re-verification (original_material_kind audit field); добавлены SOFT stopwords и 2-initial byline requirement; STEP D отложен
- **v_1_0 — 2026-01-27** — Initial release: filename generation policy для RU-журналов с приоритетом ru_authors, gene/rsID валидацией, GOST транслитерацией

---

**Конец документа**
