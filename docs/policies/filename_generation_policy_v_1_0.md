# Filename Generation Policy v_1_0

**Статус:** Canonical
**Проект:** PDF Extractor
**Область применения:** формирование имён файлов для статей из RU-журналов
**Дата:** 2026-01-27

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

**Примеры:**
```
Mg_2025-12_001-004_Contents.pdf
Mg_2025-12_005-005_Editorial.pdf
Mg_2025-12_074-080_Digest.pdf
```

---

## 4. Извлечение фамилии первого автора (Research articles)

### 4.1 Приоритет источников (RU-журналы)

Для RU-журналов (с русскоязычными метаданными) **приоритет источников инвертирован**:

**PRIMARY:** `ru_authors` anchor (русскоязычные метаданные)
- Извлекается фамилия из ru_authors
- Применяется транслитерация (GOST 7.79-2000 System B)
- **Предпочтение:** авторская транслитерация из en_authors (если доступна и валидна)

**FALLBACK:** `en_authors` anchor (англоязычные метаданные)
- Используется только если `ru_authors` отсутствует
- **Обязательна валидация** против gene/rsID паттернов

**Fail-fast:** Exit 40 (build_failed) если ни один источник не дал валидной фамилии

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
     - `ие` → `iye` (Муртазалиева → Murtazaliyeva)
     - `ню` → `niu` (Гуменюк → Gumeniuk)
   - **Source:** `ru_authors_translit`

**Примеры:**
```
Брагина → Bragina
Закля̀зьминская → Zaklyazminskaya
Муртазалиева → Murtazaliyeva (контекстное правило: ие→iye)
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

**Примеры:**
```
✅ Gandaeva    — valid surname
✅ Burykina    — valid surname
❌ TPM1        — gene symbol (all-caps, short)
❌ rs1143634   — rsID pattern
❌ TGFBR1      — gene symbol (all-caps, short)
❌ LPL         — gene symbol (all-caps, short)
```

---

## 5. Window для поиска anchors

**Определение:** window — диапазон страниц для поиска метаданных относительно начала статьи.

**Правила:**
- **ru_authors:** `[from_page, from_page+1]` (текущая страница + следующая)
- **en_authors:** `[from_page, from_page+1]` (текущая страница + следующая)

**Обоснование:** в билингвальных выпусках RU-метаданные на странице N, EN-метаданные на странице N+1.

---

## 6. Определение material_kind

**Material classification** выполняется компонентом **BoundaryDetector**.

**Типы:**
- `contents` — table of contents (multi-page)
- `editorial` — editorial/foreword (без извлекаемых авторов)
- `research` — research article (с извлекаемыми авторами)
- `digest` — digest/summary materials (journal-specific)

**Правила:**
- Если `material_kind == "contents"` → suffix `_Contents.pdf`
- Если `material_kind == "editorial"` → suffix `_Editorial.pdf`
- Если `material_kind == "digest"` → suffix `_Digest.pdf`
- Если `material_kind == "research"` → suffix `_{FirstAuthorSurname}.pdf`

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
- `evidence` (dict): детали обнаружения
  - `anchor_type` (str): `ru_authors` или `en_authors`
  - `anchor_page` (int): страница anchor
  - `en_authors_verified` (bool): была ли проверена EN фамилия (только для `ru_authors_author_translit`)

**Пример:**
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

---

## 8. Эмпирическая валидация

Политика валидирована на выпуске:
- Журнал: «Медицинская генетика»
- Выпуск: **Mg_2025-12**
- Статей: **29** (1 Contents, 1 Editorial, 27 Research)

**Результаты:**
- Golden test: **EXACT MATCH** (29/29 articles)
- Gene symbols eliminated: ✅ (TPM1, LPL, rs1143634 → valid surnames)
- ru_title/ru_authors separation: ✅ (Pathogenetics → Bragina)
- Contents/Editorial detection: ✅

**Reference:**
- Manifest: `docs/state/reference_inputs_manifest_mg_2025_12_v_1_0.json`
- Test: `tests/test_material_classification_golden.sh`

---

## 9. Ограничения и будущие улучшения

### 9.1 Текущие ограничения

- **Язык:** Политика протестирована только на RU-журналах (кириллица + латиница)
- **Транслитерация:** Контекстные правила (ие→iye, ню→niu) — эмпирические, не исчерпывающие
- **Gene validation:** Валидация проверяет известные паттерны; новые gene symbols могут потребовать обновления

### 9.2 Будущие улучшения (вне текущей версии)

- Расширение поддержки на EN-журналы (EN-first, RU-optional)
- Более полный набор контекстных правил для транслитерации (например, -ский/-ская → -sky/-skaya)
- Интеграция с внешними базами gene symbols для валидации (UniProt, HGNC)

---

## 10. Статус и правила изменения

- Документ является **каноническим источником истины** для filename generation
- Изменения допускаются **только через выпуск новой версии** (`v_1_1`, `v_2_0` и т.д.)
- Редактирование задним числом запрещено

---

## 11. CHANGELOG

- **v_1_0 — 2026-01-27** — Initial release: filename generation policy для RU-журналов с приоритетом ru_authors, gene/rsID валидацией, GOST транслитерацией

---

**Конец документа**
