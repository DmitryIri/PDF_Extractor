# PDF Extractor — Anchors Contract v1.0

**Project:** PDF Extractor  
**Status:** Canonical  
**Version:** v1.0  
**Scope:** Нормативный контракт формата `anchors[]` между MetadataExtractor → BoundaryDetector → Splitter

---

## 1. Цель

Зафиксировать минимально достаточный и воспроизводимый контракт `anchors[]`, необходимый для исполнения:
- **ArticleStartPolicy v1.0**
- **BoundaryDetector v1.0**

---

## 2. Общая структура anchor

Каждый элемент `anchors[]` — объект:

- `page` (int, 1-based) — номер страницы
- `type` (string) — тип якоря (см. раздел 3)
- `bbox` (float[4]) — `[x0, y0, x1, y1]` в координатах страницы
- `text` (string) или `value` (string) — содержимое
- `lang` (string) — `ru|en|unknown` (только для `text_block` и блоков текста)
- `font_size` (number) — только для `text_block`
- `confidence` (number) — опционально

---

## 3. Anchor Types

### 3.1 MUST (минимум для ArticleStartPolicy v1.0)

- `doi`  
  - fields: `value`, `bbox`, `page`

- `text_block`  
  - fields: `text`, `lang`, `bbox`, `font_size`, `page`

- Required RU blocks (policy 4.2):  
  - `ru_title`  
  - `ru_authors`  
  - `ru_affiliations`  
  - `ru_address`  
  - `ru_abstract`  
  - fields: `text`, `lang=ru`, `bbox`, `page`

### 3.2 SHOULD (усиливающие признаки)

RU optional (policy 4.3):
- `ru_keywords`
- `ru_for_citation`
- `ru_corresponding_author`
- `ru_funding`
- `ru_conflict_of_interest`
- `ru_received_accepted`

EN optional (policy 4.4):
- `en_title`
- `en_authors`
- `en_affiliations`
- `en_abstract`
- `en_keywords`
- `en_for_citation`
- `en_corresponding_author`
- `en_funding`
- `en_conflict_of_interest`
- `en_received_accepted`

---

## 4. Совместимость

BoundaryDetector v1.0 использует:
- `text_block` + `bbox` + `font_size` для проверки `top_40_percent` и `max font`
- required RU blocks types для выполнения обязательных условий policy
- `doi` для strong-signal S1 (через regex из policy_v1.py)

---

## 5. Изменения

Любые изменения допустимы только через выпуск новой версии `v1.1+` с явным подтверждением.
