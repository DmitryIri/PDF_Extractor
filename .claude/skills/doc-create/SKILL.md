---
name: doc-create
description: Создание нового версионированного документа с соблюдением naming convention. Используется для создания документов с нуля.
allowed-tools: Read, Write, Glob
---

# doc-create — Создание документа

**Версия:** 1.0
**Статус:** Active
**Назначение:** Single-entry point для создания новых версионированных документов в docs/**

---

## Принципы

1. **Facts-only:** Документ создаётся на основе проверяемых фактов
2. **Versioned:** Всегда v_1_0 для новых документов
3. **Naming:** `<name>_v_1_0.md` — строчные буквы, underscore, no spaces

---

## Входные данные

**Обязательно:**
- Тип документа (governance | design | policies | procedures | state | testing | plan)
- Название (строчные буквы + underscore)
- Scope / содержание

---

## Pre-gate

```bash
NAME="<name>_v_1_0.md"
BASE_NAME="<name>"
CATEGORY="<category>"

# 1. Naming convention
echo "$NAME" | grep -qE '^[a-z0-9_]+_v_[0-9]+_[0-9]+\.md$' \
  && echo "✅ Naming OK" || { echo "❌ Naming FAIL"; exit 1; }

# 2. Duplicate check
FOUND=$(find docs -name "${BASE_NAME}_v_*.md" -type f 2>/dev/null)
[ -n "$FOUND" ] && { echo "❌ Already exists: $FOUND"; exit 1; } || echo "✅ No duplicates"

# 3. Category exists
test -d "docs/$CATEGORY" && echo "✅ Category OK" \
  || { echo "❌ Category missing: docs/$CATEGORY"; exit 1; }
```

---

## Execute

### Обязательная структура нового документа

```markdown
# <Title>

**Version:** 1.0
**Status:** Draft | Active
**Last Updated:** YYYY-MM-DD
**Scope:** [Brief description]

---

## Purpose

[Why this document exists]

---

## [Main sections]

[Content — facts only, with verification commands]

---

## CHANGELOG

### v_1_0 (YYYY-MM-DD)
- Initial version
```

### Templates по типу

**design:** Context, Problem, Solution, Architecture, Verification
**policies:** Scope, Invariants, Rules, Enforcement
**state:** Current state, Verification commands
**governance:** Purpose, Principles, Rules, Enforcement

---

## Post-gate

```bash
FILE="docs/<category>/<name>_v_1_0.md"
test -f "$FILE" && echo "✅ Created" || { echo "❌ Not found"; exit 1; }
wc -l < "$FILE" | xargs -I{} test {} -ge 10 && echo "✅ Content OK"
grep -qE "^# " "$FILE" && grep -q "Version:" "$FILE" && grep -q "CHANGELOG" "$FILE" \
  && echo "✅ Sections OK" || echo "❌ Missing mandatory sections"
```

---

## CHANGELOG

### v_1_0 (2026-02-21)
- Адаптировано из server-latvia для pdf-extractor
- Убраны ссылки на single_writer_contract, project_files_index, history_log
