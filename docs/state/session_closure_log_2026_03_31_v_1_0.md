---
title: Session Closure Log 2026-03-31
version: v_1_0
date: 2026-03-31
branch: main
scope: pdf-extractor
---

# Session Closure Log — 2026-03-31 v_1_0

## 1. Мета

| Поле | Значение |
|------|---------|
| Дата | 2026-03-31 |
| Версия лога | v_1_0 |
| Ветка | main |
| Scope | pdf-extractor |
| Коммиты сессии | `c9d1df5`, `ede3839` |

---

## 2. Цель сессии

Исправить три ошибки именования файлов в выпуске Mh_2026-03:
1. `Mh_2026-03_033-039_Analiziruya.pdf` → `Mh_2026-03_033-039_Vasilkova.pdf`
2. `Mh_2026-03_055-066_Skim.pdf` → `Mh_2026-03_055-066_Plotkin.pdf`
3. `Mh_2026-03_067-070_Editorial.pdf` → `Mh_2026-03_067-070_Gelprin.pdf`

Требование: fix на уровне корневых причин, без ad-hoc patches, детерминизм, без регрессий.

---

## 3. Что было сделано

### 3.1 Forensic audit

- Установлено: ошибки 1 и 2 — `_pick_ru_authors` в MetadataExtractor выбирал running header «Том 21, № 3» (ошибка 1) и фрагмент тела статьи «ским и другим изменениям В.Д.» (ошибка 2) вместо реальных авторских byline.
- Установлено: ошибка 3 — «Гелприн М.» (иностранный автор, один инициал) не распознавался `AUTH_INITIALS_RE` (требует два инициала) → BoundaryDetector классифицировал статью как `editorial`.
- Корневая причина ошибок 1+2: в `_pick_ru_authors` не было negative gate (running headers) и positive gate (byline detection).
- Корневая причина ошибки 3: `AUTH_INITIALS_RE` требует два кириллических инициала; «М.» — один инициал → не проходит → нет `ru_authors` anchor → `editorial`.

### 3.2 Коммит c9d1df5 — running-header exclusion + positive byline gating

**`shared/author_surname_normalizer.py`:**
- Добавлена `looks_like_single_initial_byline()` с `_SINGLE_INITIAL_BYLINE_RE` (анкорировано на всю строку)
- Добавлена `looks_like_single_initial_byline_at_start()` с `_SINGLE_INITIAL_BYLINE_START_RE` (проверяет начало строки)
- Добавлены `_SINGLE_INITIAL_STRUCTURAL_LABELS` и guard по `STOPWORDS_HARD/SOFT`

**`agents/metadata_extractor/extractor.py`** (v1.3.2 → v1.3.3):
- `_pick_ru_authors`: заменён критерий `("," in t or AUTH_INITIALS_RE)` на negative gate `is_running_header` + positive gate `looks_like_author_byline / looks_like_single_initial_byline`
- `_pick_en_authors`: аналогичные ворота + вертикальное ограничение `TOP_REGION_FRAC=0.40` (предотвращает принятие библиографических ссылок снизу страницы как en_authors — регрессия p111 Davidson Mg_2025-12)
- Добавлен `sys.path` setup для standalone запуска (без PYTHONPATH)

**Тесты:**
- `tests/unit/test_author_surname_normalizer.py`: добавлен `TestLooksLikeSingleInitialByline` (18 тестов)
- `tests/unit/test_metadata_extractor_pick_authors.py`: новый файл (67 тестов)

### 3.3 Промежуточная регрессия при разработке

При добавлении `_at_start` в `_pick_en_authors` выявлена регрессия: `p68 en_authors: 'Lana R. Dzik;'` (Western-format «FirstName MI. LastName» принят за byline) → MetadataVerifier STEP A2a возвращал «Lana» вместо «Zaklyazminskaya» для Mg_2025-12 p67-73.

Решение: убрать `_at_start` из `_pick_en_authors`.

При добавлении `_at_start` в `_pick_ru_authors` выявлена вторая проблема: merged block «Гелприн М. Рассказ Майка...» (>200 символов) эмитировался как `ru_authors` → `_is_editorial_greeting()` в BoundaryDetector возвращал `True` (len > 200) → статья всё равно классифицировалась как `editorial`.

### 3.4 Коммит ede3839 — single-initial byline prefix extraction

**`shared/author_surname_normalizer.py`:**
- Добавлена `extract_single_initial_byline_prefix()`: возвращает только prefix byline («Гелприн М.») из merged block («Гелприн М. Рассказ Майка...»)

**`agents/metadata_extractor/extractor.py`:**
- `_pick_ru_authors`: вместо `_at_start` использует `extract_single_initial_byline_prefix`; возвращает `{**c, "text": prefix}` — только byline token, не весь merged block
- `_pick_en_authors`: `_at_start` убран (false positive в EN path)

**Тесты:**
- `tests/unit/test_author_surname_normalizer.py`: добавлен `TestExtractSingleInitialBylinePrefix` (8 тестов)

---

## 4. Изменения

### Code
| Файл | Тип изменения |
|------|--------------|
| `shared/author_surname_normalizer.py` | добавлены 3 новые функции + typing import |
| `agents/metadata_extractor/extractor.py` | v1.3.2 → v1.3.3; `_pick_ru/en_authors` переписаны |
| `tests/unit/test_author_surname_normalizer.py` | +26 тестов (2 новых класса) |
| `tests/unit/test_metadata_extractor_pick_authors.py` | новый файл, 67 тестов |

### Docs
Нет изменений в docs/

### Server / Runtime
- Export: `/srv/pdf-extractor/exports/Mh/2026/Mh_2026-03/exports/2026_03_31__19_33_33/`
- 9 статей: T=L=E=9, sha256 verified

---

## 5. Принятые решения

1. **`_at_start` только в RU path** — не применяется в `_pick_en_authors`. Причина: Western-format «FirstName MI. LastName;» (в секциях корреспонденции) создаёт false positive. Single-initial авторы типа «Gelprin M.» корректно обрабатываются через RU path.

2. **Эмитировать только prefix, не merged block** — `_pick_ru_authors` возвращает `{**c, "text": prefix}` вместо полного merged candidate. Причина: `_is_editorial_greeting()` в BoundaryDetector отвергает любой `ru_authors` текст >200 символов.

3. **Vertical constraint в `_pick_en_authors`** (`TOP_REGION_FRAC=0.40`) — постоянное решение для предотвращения принятия библиографических ссылок с нижней части страницы как en_authors.

4. **`material_kind='editorial'` = «нет extractable authors»** — подтверждена семантика: editorial ≠ «нет полных RU blocks»; editorial = «нет авторского byline». Gelprin HAS автора → bug detection, не policy change.

---

## 6. Риски / проблемы

- **`_SINGLE_INITIAL_BYLINE_START_RE` и Western-format имена**: риск False Positive существует если в EN-only журналах корреспондентские секции в TOP_REGION_FRAC страницы. Текущая митигация: `_at_start` убрана из EN path.
- **`_is_editorial_greeting` len>200 heuristic**: широкий guard, может отвергать корректные multi-author bylines если они сливаются с аффилиациями при grouping. Не наблюдалось на текущих тестовых данных.

---

## 7. Открытые вопросы

- **Q9 (перенесено)**: `http://localhost:18080` не открывается (висит в статусе «загрузка»). Не диагностировано. Проверить: SSH tunnel активен? `systemctl status pdf-extractor-ui`? `ss -tlnp | grep 8080`?
- **Q1**: Golden test для Mh_2026-02 (аналог mg_2025_12) — не создан.
- **Q2**: MetadataExtractor выбирает рубрику вместо ru_title (журнал Mh) — отложено.
- **Q7**: UI AC1–AC7 (e2e тест с реальным PDF через http://localhost:18080) — не выполнено.
- **Q8**: Решить — делать GitHub repo public или отдельный portfolio fork.

---

## 8. Точка остановки

**Где остановились:** Mh_2026-03 обработан, все три ошибки именования исправлены, коммит `ede3839` в main.

**Следующий шаг:** Диагностика Q9 (UI недоступен) → проверить SSH tunnel + `systemctl status pdf-extractor-ui`.

**Блокеры:** Нет.

---

## 9. Ссылки на актуальные документы

- TechSpec: `docs/design/pdf_extractor_techspec_v_2_8.md`
- Filename Generation Policy: `docs/policies/filename_generation_policy_v_1_2.md`
- Article Start Detection Policy: `docs/policies/article_start_detection_policy_v_1_0.md`
- project_summary: `docs/state/project_summary_v_2_15.md`
- project_files_index: `docs/governance/project_files_index.md`

---

## CHANGELOG

### v_1_0 (2026-03-31)
- Создан по итогам сессии 2026-03-31
- Охватывает: forensic audit Mh_2026-03, fix `_pick_ru/en_authors`, single-initial support, prefix extraction
