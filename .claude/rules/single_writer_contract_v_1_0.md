---
rule: single-writer-contract
version: 1.0
status: Active
scope: docs/** modifications
enforcement: Convention (pre-commit hook — planned)
---

# Single Writer Contract

**Версия:** 1.0
**Статус:** Active
**Дата:** 2026-02-21
**Scope:** Все изменения в `docs/**`

---

## Принцип

> **Doc-Agent является единственным авторизованным writer для `docs/**`.**

Любые модификации документации (create, update, rename, delete) ДОЛЖНЫ происходить ТОЛЬКО через Doc-Agent и его skills.

---

## Invariant (CRITICAL)

```
❌ ЗАПРЕЩЕНО: прямые изменения docs/** не через Doc-Agent

✅ РАЗРЕШЕНО: только через Doc-Agent skills
  - /doc-create   — создание нового документа
  - /doc-update   — version bump существующего
  - /doc-index    — синхронизация project_files_index
  - /doc-review   — read-only проверка (нет изменений)
```

---

## Запреты (Explicit)

### ❌ Запрещённые операции:

**1. Прямое создание файлов:**
```bash
# ❌ FORBIDDEN
touch docs/design/new_file.md
```

**2. Прямое редактирование:**
```bash
# ❌ FORBIDDEN
vim docs/policies/policy_v_1_0.md
# ❌ FORBIDDEN — прямое редактирование через IDE
```

**3. Прямое переименование:**
```bash
# ❌ FORBIDDEN
mv docs/state/old_name.md docs/state/new_name.md
git mv docs/policies/file.md docs/policies/renamed.md
```

**4. Прямое удаление:**
```bash
# ❌ FORBIDDEN
rm docs/design/obsolete.md
git rm docs/policies/deprecated.md
```

**5. Batch operations без Doc-Agent:**
```bash
# ❌ FORBIDDEN
find docs -name "*.md" -exec sed -i 's/old/new/g' {} \;
```

---

## Разрешённые операции

### ✅ Через Doc-Agent skills:

**Create:**
```
/doc-create
```

**Update (version bump):**
```
/doc-update
```

**Index sync:**
```
/doc-index
```

**Review:**
```
/doc-review  # Read-only, safe
```

---

## Исключения

### Exception 1: Emergency Fix

**Условие:** Critical issue требует немедленного исправления в docs/

**Procedure:**
1. Make emergency change (direct edit)
2. **ОБЯЗАТЕЛЬНО:** Зафиксировать в следующем session_closure_log с justification
3. Review через `/doc-review` после исправления
4. Notify в commit message: `fix(docs): emergency fix — <reason>`

### Exception 2: Initial Bootstrap

**Условие:** Инициализация проекта, Doc-Agent ещё не настроен

**Allowed:** Прямое создание файлов ДО первого commit с Doc-Agent skills

**После bootstrap:** Single Writer Contract активируется

---

## Enforcement

### Текущий статус (v_1_0)
- **Convention:** Claude Code соблюдает контракт поведенчески
- **Pre-commit hook:** planned (future — автоматическая детекция прямых коммитов в docs/**)

### Planned pre-commit check
```bash
# Detect direct commits to docs/** без Doc-Agent
git diff --cached --name-only | grep "^docs/" | while read file; do
  echo "⚠️  Direct commit to docs/** detected: $file"
  echo "   Use Doc-Agent skills for doc changes."
done
```

---

## Audit Trail

Операции Doc-Agent логируются в:
- `_audit/claude_code/` — session-level артефакты
- commit messages — описание изменений doc

---

## Integration с Governance

**References:**
- `docs/governance/versioning_policy.md` — immutability, version bumps
- `docs/governance/documentation_rules_style_guide.md` — facts-only
- `docs/governance/project_files_index.md` — canonical registry
- `.claude/agents/doc-agent.md` — Doc-Agent spec

---

## CHANGELOG

### v_1_0 (2026-02-21)
- Initial version для pdf-extractor
- Адаптировано из server-latvia single_writer_contract_v_1_0.md
- Убраны: DPR/doc-patch механизм, history_log (нет в pdf-extractor)
- Убран: doc-migrate (миграция уже выполнена)
- Enforcement: конвенция (pre-commit hook — planned)
- 4 разрешённых skills вместо 6
