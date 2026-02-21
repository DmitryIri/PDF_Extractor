---
name: doc-review
description: Read-only consistency checks для документации pdf-extractor. Проверяет naming, versions, immutability. Не изменяет файлы.
allowed-tools: Read, Grep, Glob, Bash
---

# doc-review — Documentation Consistency Check

**Версия:** 1.0
**Статус:** Active
**Назначение:** Read-only валидация docs/**

---

## Принципы

1. **Read-only:** NO modifications
2. **Actionable:** Каждая ошибка → recommendation как исправить
3. **Facts-only:** Только проверяемые факты

---

## Checks

### Check 1: Naming convention
```bash
# Исключения:
# - docs/governance/*.md — evergreen pattern (версия внутри, не в filename)
# - docs/_archive/ — legacy files до миграции (не переименовываем)
# - docs/state/project_history_log.md — evergreen (кумулятивный лог)
# - docs/state/execution_report_*.md — report format (не closure log)
# - README.md — стандартный

find docs -name "*.md" -type f \
  | grep -v "_v_[0-9]\+_[0-9]\+\.md$" \
  | grep -v "README.md" \
  | grep -v "^docs/governance/" \
  | grep -v "^docs/_archive/" \
  | grep -v "docs/state/project_history_log\.md" \
  | grep -v "docs/state/execution_report_"
# Expected: empty (все оставшиеся файлы versioned)
```

### Check 2: Immutability (нет uncommitted changes к committed versioned files)
```bash
git diff --name-only | grep "_v_[0-9]\+_[0-9]\+\.md$"
# Expected: empty
```

### Check 3: Version metadata sync (filename version == file content version)
```bash
# Применяется только к versioned файлам (с _v_X_Y в имени), вне _archive/
# Поддерживает оба формата: "**Version:** X.Y" и "**Версия:** v_X_Y"
for f in $(find docs -name "*_v_*_*.md" -type f | grep -v "_archive/"); do
  fn_ver=$(basename "$f" | grep -oP 'v_\K[0-9]+_[0-9]+' | tr '_' '.')
  # Поддержка английского и русского полей версии
  fc_ver=$(grep -E "^\*\*(Version|Версия):\*\*" "$f" \
    | grep -oP '[0-9]+[._][0-9]+' | head -1 | tr '_' '.')
  [ -z "$fc_ver" ] && fc_ver="(no version field)"
  [ "$fn_ver" != "$fc_ver" ] && echo "MISMATCH: $f  filename=$fn_ver  content=$fc_ver"
done
# Expected: empty для canonical files (policies/, design/, state/)
```

### Check 4: No stale version references in CLAUDE.md
```bash
# Проверить что версии компонентов в CLAUDE.md соответствуют актуальным
grep -E "v_[0-9]+_[0-9]+" CLAUDE.md
# Сравнить с VERSION = "..." в agents/**/*.py
```

### Check 5: Index sync (project_files_index актуален)
```bash
# Governance docs используют evergreen name: docs/governance/project_files_index.md
INDEX_FILE="docs/governance/project_files_index.md"
echo "Index: $INDEX_FILE"
test -f "$INDEX_FILE" || echo "ERROR: index file not found"

# Шаг 2: Найти canonical файлы в docs/ НЕ перечисленные в индексе
# Scope: только active canonical (вне _archive/)
# Исключения:
# - session_closure_log_* — покрываются generic pattern в индексе (не перечисляются индивидуально)
for f in $(find docs -name "*_v_*_*.md" -type f | grep -v "_archive/" \
           | grep -v "session_closure_log_" | sort); do
  bname=$(basename "$f")
  grep -q "$bname" "$INDEX_FILE" || echo "MISSING from index: $f"
done
# Expected: empty (все active canonical docs индексированы)

# Шаг 3: Orphan check — entries в индексе без реального файла
# (manual check: grep filenames from index, verify they exist on disk)
```

---

## Output Format

```
# doc-review Report — YYYY-MM-DD

✅ Check 1: Naming — all files versioned
✅ Check 2: Immutability — no uncommitted changes
⚠️  Check 3: Version sync — 1 mismatch found
✅ Check 4: No stale refs
⚠️  Check 5: Index sync — 2 files missing from index

Issues:
- docs/design/foo_v_1_0.md: filename=1.0, content=1.1
  Fix: /doc-update (version bump to v_1_1)
- docs/policies/bar_v_1_2.md: not in project_files_index
  Fix: /doc-index
```

---

## CHANGELOG

### v_1_2 (2026-02-21)
- Check 1: добавлены исключения docs/governance/ (evergreen), docs/_archive/ (legacy), project_history_log.md, execution_report_*
- Check 3: поддержка русского поля "**Версия:**" (дополнительно к "**Version:**"); scope ограничен active files (вне _archive/)
- Check 5: исправлен path — docs/governance/project_files_index.md (evergreen name, без версии в filename)

### v_1_1 (2026-02-21)
- Добавлен Check 5: index sync (project_files_index актуален)
- Обновлён Output Format: 5 checks

### v_1_0 (2026-02-21)
- Адаптировано из server-latvia для pdf-extractor
- Упрощён Check 4: специфичен для CLAUDE.md + agents/**/*.py
