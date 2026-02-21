---
name: doc-index
description: Обновление project_files_index после создания/изменения/удаления файлов в docs/**. Сканирует docs/, сравнивает с текущим индексом, применяет version bump.
allowed-tools: Read, Write, Glob, Grep, Bash
---

# doc-index — Project Files Index Sync

**Версия:** 1.0
**Статус:** Active
**Назначение:** Синхронизация `docs/governance/project_files_index_v_X_Y.md` после изменений в docs/**

---

## Принципы

1. **Safe:** Только index write — не трогает другие docs/**
2. **Idempotent:** Повторный запуск без изменений → без побочных эффектов
3. **Auditable:** Diff preview перед применением

---

## Pre-gate

### Gate 1: Index exists
```bash
ls docs/governance/project_files_index_v_*.md
# Expected: минимум один файл
```

### Gate 2: Scan docs/
```bash
find docs -name "*_v_*_*.md" -type f | sort
# Expected: список всех версионированных файлов
```

### Gate 3: Parse current index
```bash
# Определить последнюю версию index
INDEX_FILE=$(ls docs/governance/project_files_index_v_*.md | sort -V | tail -1)
echo "Current index: $INDEX_FILE"
```

---

## Execute

### Шаг 1: Detect changes

Сравнить файлы из `find docs -name "*_v_*_*.md"` с файлами в текущем индексе:

- **Added:** файлы в docs/ но НЕ в индексе
- **Removed:** файлы в индексе но НЕ в docs/ (удалённые/архивированные)

Также проверить `.claude/agents/`, `.claude/skills/`, `.claude/rules/` на предмет новых файлов если они включены в индекс.

### Шаг 2: Propose update (diff preview)

Вывести diff перед применением:
```
Added entries:
  + docs/policies/filename_generation_policy_v_1_2.md
  + docs/design/pdf_extractor_techspec_v_2_7.md

Removed entries:
  (none)
```

### Шаг 3: Decision — version bump vs in-place

```
Если текущий INDEX_FILE в git (committed):
  → Version bump: INDEX_FILE_v_X_Y+1.md (MINOR bump для additive changes)

Если INDEX_FILE НЕ в git (uncommitted):
  → In-place edit (без version bump)
```

**Проверка:**
```bash
git ls-files --error-unmatch "$INDEX_FILE" 2>/dev/null && echo "committed" || echo "uncommitted"
```

### Шаг 4: Apply update

**Mode A: Version bump**
1. Определить новую версию: `v_X_Y` → `v_X_{Y+1}`
2. Скопировать содержимое старого файла в новый
3. Добавить новые entries в соответствующие секции
4. Обновить счётчик "Total files"
5. Добавить CHANGELOG entry в новый файл

**Mode B: In-place edit**
1. Добавить новые entries в существующий файл
2. Обновить счётчик "Total files"
3. Обновить CHANGELOG note

---

## Post-gate

### Gate 1: Index updated
```bash
# Для Mode A
test -f docs/governance/project_files_index_v_X_{Y+1}.md && echo "OK"
```

### Gate 2: All current docs indexed (NO missing files)
```bash
# Каждый файл из find docs -name "*_v_*_*.md" должен быть в индексе
for f in $(find docs -name "*_v_*_*.md" -type f); do
  grep -q "$(basename $f)" docs/governance/project_files_index_v_*.md \
    || echo "MISSING: $f"
done
# Expected: empty
```

### Gate 3: NO orphaned entries
```bash
# Каждый файл в индексе должен существовать
# (Выполнить grep поиск имён файлов из индекса)
```

---

## Index File Format

Структура секций (4 класса документов):

```markdown
## 1. Governance / Meta
| Файл | Версия | Назначение | Статус |
|------|--------|------------|--------|
| `docs/governance/versioning_policy_v_2_0.md` | v_2_0 | Правила версионирования | Canonical |

## 2. Project State (As-Is)
| Файл | Версия | Назначение | Статус |
|------|--------|------------|--------|
| `docs/state/project_summary_v_X_Y.md` | v_X_Y | Текущее состояние проекта | Canonical |

## 3. Project Design (To-Be)
| Файл | Версия | Назначение | Статус |
|------|--------|------------|--------|
| `docs/design/pdf_extractor_techspec_v_X_Y.md` | v_X_Y | Техническое задание | Canonical |

## 4. Policy Documents
| Файл | Версия | Назначение | Статус |
|------|--------|------------|--------|
| `docs/policies/article_start_detection_policy_v_1_0.md` | v_1_0 | Политика детекции статей | Canonical |
```

---

## Triggers

Вызывается:
- После `/doc-create` — добавить новый файл в индекс
- После `/doc-update` — обновить версию файла в индексе
- После ручного создания документа (bootstrap/emergency)
- По запросу пользователя для синхронизации

---

## Output Format

```
✅ doc-index complete
   Index: project_files_index_v_1_8.md → project_files_index_v_1_9.md
   Added: 3 entries
   Removed: 0 entries
   Total files: 42

   Verification: ls docs/governance/project_files_index_v_1_9.md
   Expected: file exists
```

---

## CHANGELOG

### v_1_0 (2026-02-21)
- Initial version для pdf-extractor
- Адаптировано из server-latvia doc-index/SKILL.md
- Убраны: history_log entries (нет в pdf-extractor)
- Scope: 4 categories (Governance, State, Design, Policy)
- Добавлены .claude/ artifacts в scan scope
