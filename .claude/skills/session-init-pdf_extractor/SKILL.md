---
name: session-init-pdf_extractor
description: Session kickoff workflow for pdf-extractor project. Reads context from allowed dirs only (/opt/projects/pdf-extractor + ~/.claude). No /srv/* access required.
---

# session-init-pdf_extractor

## Purpose

Project-specific session start for pdf-extractor. Reads project state entirely from:
- `/opt/projects/pdf-extractor/` (repo)
- `~/.claude/projects/-opt-projects-pdf-extractor/memory/MEMORY.md` (persistent memory)

**No access to `/srv/*` or other restricted paths.**

---

## Inputs

None.

---

## Allowed paths (CRITICAL)

This skill MUST NOT execute commands targeting paths outside:
- `/opt/projects/pdf-extractor/`
- `/home/dmitry/.claude/`

All file reads → use **Read tool** (not Bash cat).
All file listings → use **Glob tool** (not Bash ls/find).
Bash commands → only: `git status -sb`, `git log`, `git rev-parse`, `date`.

---

## Procedure

### Step 1 — T1: Check root for export artifacts

Use **Bash**:
```bash
git status -sb
```

Scan output for untracked files matching patterns:
- `conversation-*.txt`
- `*-task-*.txt`
- `*-claude-code-*.txt`

If any match found → **STOP** and output:
```
⚠️ T1: В корне репозитория есть export-артефакты: [список]
Предлагаю запустить /archive-exports перед продолжением.
```
Do NOT proceed until T1 is resolved.

---

### Step 2 — Gather context (read-only, allowed dirs only)

Execute the following in this exact order:

**2a. Read MEMORY.md** (use Read tool):
```
/home/dmitry/.claude/projects/-opt-projects-pdf-extractor/memory/MEMORY.md
```

**2b. Find latest session closure log** (use Glob tool):
```
docs/state/session_closure_log_*.md
```
Pick file with latest mtime. Read it (use Read tool). Extract:
- Open items / pending tasks
- Next steps

**2c. Version discovery** (use Glob tool — find active versions, not archived):
```
docs/design/pdf_extractor_techspec_v_*.md     → latest by version suffix
docs/design/pdf_extractor_plan_v_*.md          → latest by version suffix
docs/state/project_summary_v_*.md              → latest by version suffix
```
Exclude `docs/_archive/` from results.

**2d. Git context** (use Bash, separate calls):
```bash
git rev-parse --short HEAD
```
```bash
git log --oneline -5
```

---

### Step 3 — Build and output kickoff

Output the following structure (facts only, no inventions):

```
## Session Kickoff — YYYY-MM-DD

**Проект:** PDF Extractor — детерминированный multi-agent pipeline для извлечения статей из PDF-журналов

---

### Статус (из MEMORY.md)

| Компонент/Фаза | Версия | Статус |
|---|---|---|
| MetadataExtractor | v1.3.2 | ✅ |
| BoundaryDetector | v1.3.1 | ✅ |
| MetadataVerifier | v1.4.0 | ✅ |
| OutputBuilder | v1.2.0 | ✅ |
| ... | ... | ... |

**Последние production runs:**
- <из MEMORY.md>

---

### Active docs (фактические версии)

- TechSpec: <файл из Glob>
- Plan: <файл из Glob>
- project_summary: <файл из Glob>

---

### Open items / Pending tasks

<из MEMORY.md раздел "Open questions / Pending tasks">

---

### Рекомендуемая задача

**<Конкретная задача>**

<2–3 предложения: почему сейчас, точка входа (файл/команда)>

---

*Branch: main · HEAD: <sha> · Дата: <date>*
```

**Rules:**
- Facts only. No invented status.
- Primary source: MEMORY.md `## Open questions / Pending tasks`.
- Secondary source: latest session_closure_log.
- If MEMORY.md not found → derive from CLAUDE.md + git log.
- Recommended task must have specific entry point.
  Good: "Запустить `/doc-update` для project_summary v_2_12 → v_2_13 (файл: docs/state/project_summary_v_2_12.md)"
  Bad: "Обновить документацию"

---

### Step 4 — One question

After kickoff output, ask exactly ONE question:

```
Подтверждаешь задачу или у тебя другой приоритет?
```

Do NOT ask multiple questions. Do NOT start implementation until confirmed.

---

### Step 5 — After confirmation (optional, on request)

Only if user confirms:
1. **Skill audit:** Which skills/agents needed for confirmed task
2. **Doc check:** Is relevant doc sufficient? (read SKILL.md or spec if exists)
3. **Gap:** If docs missing → propose `/doc-create`

---

## Error handling

| Situation | Action |
|---|---|
| MEMORY.md not found | Note it, derive from CLAUDE.md + git log |
| No closure logs | Note "первая сессия или лог не найден" |
| Git not available | Skip git steps, note absence |
| T1 not resolved | STOP, do not proceed with kickoff |

---

## What this skill does NOT do

- Does NOT read `/srv/*` paths
- Does NOT use `$()` command substitution
- Does NOT chain commands with `&&` in Bash (each command = separate Bash call)
- Does NOT auto-start implementation
- Does NOT check server-latvia daily gate or transfer bundles

---

## Version

**v_1_0** · 2026-03-04
**Scope:** pdf-extractor project only
**Supersedes:** global `session-init` for pdf-extractor context (which fails on `/srv/server-latvia/` path)
