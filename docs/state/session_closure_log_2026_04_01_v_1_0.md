---
title: Session Closure Log 2026-04-01
version: v_1_0
date: 2026-04-01
branch: main
scope: pdf-extractor
---

# Session Closure Log — 2026-04-01 v_1_0

## 1. Мета

| Поле | Значение |
|------|---------|
| Дата | 2026-04-01 |
| Версия лога | v_1_0 |
| Ветка | main |
| Scope | pdf-extractor |
| Коммит сессии | `0e359b7` |

---

## 2. Цель сессии

Каноническое документарное закрытие (doc-closure) уже реализованного fix'а по ошибкам именования
файлов в Mh_2026-03. Кодовый fix реализован в предыдущей сессии (commits c9d1df5, ede3839).
Цель текущей сессии — устранить drift между кодом и канонической документацией: зафиксировать
поддержку single-initial byline (RU path), EN false-positive guardrail, обновить policy, history,
summary, index, registry.

---

## 3. Что было сделано

### 3.1 Созданы новые версии документов

**`filename_generation_policy_v_1_3.md`** (новый файл, bump от v_1_2):
- Добавлен §4.7 «Выбор ru_authors кандидатов»: документированы negative gate
  (`is_running_header`) + positive gate (`looks_like_author_byline` /
  `looks_like_single_initial_byline` / `extract_single_initial_byline_prefix`);
  семантический инвариант (naming зависит от upstream extraction, не post-hoc substitution)
- §8: добавлен acceptance fixture Mh_2026-03 (9 статей, 3 исправленных filename)
- §9.1: пункт о single-initial переписан — ограничение больше не абсолютно; RU path
  контролируемо поддерживает; EN-path намеренно исключён
- §11: CHANGELOG entry v_1_3

**`project_summary_v_2_16.md`** (новый файл, bump от v_2_15):
- MetadataExtractor v1.3.2 → v1.3.3
- Новые milestones: RU Single-Initial Byline Fix + Mh_2026-03 Production Validation
- §5 Policies: v_1_2 → superseded, v_1_3 → canonical
- §7 Invariants: FilenameGenerationPolicy v_1_3
- §10: production validated journals — добавлен Mh (2026-03)

### 3.2 Обновлены существующие документы

**`project_history_log.md`** — добавлена запись 2026-03-31:
- Trigger-выпуск Mh_2026-03, 3 ошибочных filename, описание fix'а на уровне extractor,
  EN false-positive risk и нейтрализация, validation результат.

**`project_files_index.md`** (v_1_15 → v_1_16):
- §2.E: policy v_1_3 canonical, v_1_2 superseded
- §2.B: summary v_2_16 canonical, v_2_15 superseded
- §5 Physical paths: обновлены пути docs/policies/
- CHANGELOG entry v_1_16

**`canonical_artifact_registry.md`** (v_1_2 → v_1_3):
- §5.1: canonical policy обновлён с v_1_1 до v_1_3 (исправлен накопленный drift)
- CHANGELOG entry v_1_3

### 3.3 Коммит и push

- Коммит `0e359b7` — 5 файлов, +838 строк
- Push: auto-push hook + ручной push (оба успешны); GitHub зеркало актуально

---

## 4. Изменения

### Code
Нет изменений в коде pipeline (`agents/`, `shared/`, `tools/`, `ui/`).

### Docs
| Файл | Тип |
|------|-----|
| `docs/policies/filename_generation_policy_v_1_3.md` | CREATE |
| `docs/state/project_summary_v_2_16.md` | CREATE |
| `docs/state/project_history_log.md` | APPEND (+15 строк) |
| `docs/governance/project_files_index.md` | EDIT (v_1_15→v_1_16, +12 строк) |
| `docs/governance/canonical_artifact_registry.md` | EDIT (v_1_2→v_1_3, +5 строк) |

### Server / Runtime
Нет изменений в runtime окружении.

---

## 5. Принятые решения

1. **Минимальный patch-diff** для policy v_1_3: добавлен §4.7 и обновлён §9.1; остальные
   разделы без изменений. Причина: doc-closure, не rewrite.

2. **canonical_artifact_registry обновлён до v_1_3** несмотря на то, что он уже имел
   drift v_1_1 → v_1_2 → v_1_3. Причина: registry должен отражать текущий canonical pointer;
   исправление накопленного drift входит в scope doc-closure.

3. **EN-path guardrail зафиксирован в двух местах** (§4.7 + §9.1) для явности. Причина:
   задача требует зафиксировать не только что поддерживается, но и что намеренно исключено
   и почему.

---

## 6. Риски / проблемы

- **Агент прервался по лимиту сессии** в середине выполнения: первый вызов doc-agent
  завершился по timeout. Три из пяти документов были созданы до прерывания;
  оставшиеся два выполнены вторым вызовом. Итоговое состояние корректно.

---

## 7. Открытые вопросы

- **Q9 (priority):** `http://localhost:18080` не открывается (висит). Не диагностировано.
  Проверить: SSH tunnel активен? `systemctl status pdf-extractor-ui`? `ss -tlnp | grep 8080`?
- **Q7:** UI AC1–AC7 — e2e тест с реальным PDF через http://localhost:18080 — не выполнено.
- **Q8:** Решить — делать GitHub repo public или отдельный portfolio fork.
- **Q1:** Golden test для Mh_2026-02 (аналог mg_2025_12) — не создан.
- **Q2:** MetadataExtractor выбирает рубрику вместо ru_title (журнал Mh) — отложено.

---

## 8. Точка остановки

**Где остановились:** doc-closure задача завершена полностью. Commit `0e359b7` в main.

**Следующий шаг:** Диагностика Q9 (UI недоступен) — проверить SSH tunnel +
`systemctl status pdf-extractor-ui`.

**Блокеры:** Нет.

---

## 9. Ссылки на актуальные документы

- TechSpec: `docs/design/pdf_extractor_techspec_v_2_8.md`
- Filename Generation Policy: `docs/policies/filename_generation_policy_v_1_3.md`
- Article Start Detection Policy: `docs/policies/article_start_detection_policy_v_1_0.md`
- project_summary: `docs/state/project_summary_v_2_16.md`
- project_files_index: `docs/governance/project_files_index.md` (v_1_16)

---

## CHANGELOG

### v_1_0 (2026-04-01)
- Создан по итогам сессии 2026-04-01
- Охватывает: doc-closure для Mh_2026-03 byline fix; policy v_1_3; summary v_2_16;
  history_log; index v_1_16; registry v_1_3
