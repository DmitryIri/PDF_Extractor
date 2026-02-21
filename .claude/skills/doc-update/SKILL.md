---
name: doc-update
description: Обновление существующего версионированного документа через version bump. Соблюдает immutability старых версий и создаёт новую версию с изменениями.
allowed-tools: Read, Write, Edit, Glob
---

# doc-update — Обновление документа

**Версия:** 1.0
**Статус:** Active
**Назначение:** Version bump для существующих docs/** с соблюдением immutability

---

## Принципы

1. **Immutability:** Старая версия НЕ изменяется после commit
2. **Version bump:** Major (breaking) или Minor (additive)
3. **CHANGELOG:** Обязательная запись изменений
4. **Facts-only:** Документ содержит только проверяемые факты

---

## Входные данные

**Обязательно:**
- Существующий документ (путь или имя)
- Тип изменения: major | minor | typo
- Описание изменений (для CHANGELOG)

**Опционально:**
- Конкретные изменения (diff content)

---

## Pre-gate (проверки перед обновлением)

### Проверка 1: File exists
```bash
# Найти latest version документа
find docs -name "<name>_v_*.md" -type f | sort -V | tail -1

# HALT если файл не найден
# Предложить: использовать /doc-create для новых документов
```

### Проверка 2: Immutability check
```bash
# Проверить, что файл закоммичен (immutable)
git ls-files docs/<category>/<name>_v_X_Y.md

# Если НЕ в git (uncommitted):
# - Разрешить in-place edit (без version bump)
# - Это исключение для typo fixes до commit

# Если в git (committed):
# - ТРЕБУЕТСЯ version bump
# - Старый файл immutable
```

### Проверка 3: Version bump calculation
```
# Major bump (v_2_3 → v_3_0): Breaking changes, architecture redesign
# Minor bump (v_2_3 → v_2_4): New requirements, additive changes, compatible
# No bump (typo/formatting): ТОЛЬКО если uncommitted
```

---

## Execute (обновление документа)

### Режим 1: Version bump (committed file)

**Шаг 1: Create new version file**
- Read полное содержимое старого файла
- Создать новый файл с именем `<name>_v_X_Y+1.md`
- Применить изменения к контенту

**Шаг 2: Update metadata в новом файле**
```markdown
**Version:** X.Y+1
**Last Updated:** YYYY-MM-DD
```

**Шаг 3: Добавить CHANGELOG entry**
```markdown
### v_X_Y+1 (YYYY-MM-DD)
- [Change description 1]
- [Change description 2]
```

**Шаг 4: Verify old version untouched**
```bash
git diff docs/<category>/<name>_v_X_Y.md
# Expected: пустой вывод (старая версия не изменена)
```

---

### Режим 2: In-place edit (uncommitted typo)

**Условие:** Файл НЕ в git (`git ls-files <file>` возвращает пустой вывод)

Редактировать файл напрямую, добавить note в CHANGELOG без version bump.

---

## Post-gate

```bash
# Проверить новый файл создан
ls -la docs/<category>/<name>_v_X_Y+1.md

# Проверить CHANGELOG обновлён
grep "### v_X_Y+1" docs/<category>/<name>_v_X_Y+1.md

# Убедиться старый файл не изменён
git diff docs/<category>/<name>_v_X_Y.md
```

---

## Version Bump Decision Matrix

| Change Type       | Committed? | Action                           |
|-------------------|-----------|----------------------------------|
| Breaking change   | Yes        | Major bump (v_2_3 → v_3_0)      |
| New requirement   | Yes        | Minor bump (v_2_3 → v_2_4)      |
| Clarification     | Yes        | Minor bump (v_2_3 → v_2_4)      |
| Typo/formatting   | No         | In-place edit                    |
| Typo/formatting   | Yes        | Minor bump (optional)            |

---

## CHANGELOG

### v_1_0 (2026-02-21)
- Адаптировано из server-latvia для pdf-extractor
- Убраны ссылки на single_writer_contract, project_files_index, history_log
- Core logic сохранён: version bump, immutability, CHANGELOG
