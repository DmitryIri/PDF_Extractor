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
find docs -name "*.md" -type f \
  | grep -v "_v_[0-9]\+_[0-9]\+\.md$" \
  | grep -v "README.md"
# Expected: empty (все файлы versioned)
```

### Check 2: Immutability (нет uncommitted changes к committed versioned files)
```bash
git diff --name-only | grep "_v_[0-9]\+_[0-9]\+\.md$"
# Expected: empty
```

### Check 3: Version metadata sync (filename version == file content version)
```bash
# For each versioned doc: extract version from filename и из **Version:** поля
# Сравнить — должны совпадать
for f in $(find docs -name "*_v_*_*.md" -type f); do
  fn_ver=$(basename "$f" | grep -oP 'v_\K[0-9]+_[0-9]+' | tr '_' '.')
  fc_ver=$(grep "^\*\*Version:\*\*" "$f" | grep -oP '[0-9]+\.[0-9]+' | head -1)
  [ "$fn_ver" != "$fc_ver" ] && echo "MISMATCH: $f (file=$fn_ver, content=$fc_ver)"
done
```

### Check 4: No stale version references in CLAUDE.md
```bash
# Проверить что версии компонентов в CLAUDE.md соответствуют актуальным
grep -E "v_[0-9]+_[0-9]+" CLAUDE.md
# Сравнить с VERSION = "..." в agents/**/*.py
```

---

## Output Format

```
# doc-review Report — YYYY-MM-DD

✅ Check 1: Naming — all files versioned
✅ Check 2: Immutability — no uncommitted changes
⚠️  Check 3: Version sync — 1 mismatch found
✅ Check 4: No stale refs

Issues:
- docs/design/foo_v_1_0.md: filename=1.0, content=1.1
  Fix: /doc-update (version bump to v_1_1)
```

---

## CHANGELOG

### v_1_0 (2026-02-21)
- Адаптировано из server-latvia для pdf-extractor
- Упрощён Check 4: специфичен для CLAUDE.md + agents/**/*.py
- Убраны Check 5 (index sync) и Check 6 (facts-only): нет project_files_index в pdf-extractor
