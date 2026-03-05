---
name: session-close-pdf_extractor
description: Session closure workflow for pdf-extractor project. Archive /export artifacts, draft session_closure_log, enforce _audit gitignore discipline.
---

# session-close-pdf_extractor

## Purpose
Single entrypoint for "Завершение сессии" for pdf-extractor.
Full canonical closure workflow:
1) Detect and archive Claude Code /export artifacts from repo root (via /archive-exports; deletion requires user confirmation).
2) Draft `session_closure_log_YYYY_MM_DD_v_X_Y.md` (content + suggested path) using repo facts only.
3) Provide final verification commands and enforce `_audit/**` non-tracking.

## Inputs
None.

## Automation default
**Default behavior:** Claude Code MUST run all required repo commands itself to collect facts.
**Fallback only:** If a command cannot be executed (no tool access / error), then request the minimum required user-run commands.

## Preconditions (facts)
- Repo root is accessible.
- Skill exists: /archive-exports

If /archive-exports is missing, STOP and output:
- ls -la .claude/skills
- ls -la .claude/skills/archive-exports

## Source of Truth (canonical docs)
- session_closure_protocol.md
- session_finalization_playbook.md
- documentation_rules_style_guide.md
- versioning_policy.md

This skill must follow those documents and must not invent facts.

## Procedure (deterministic, automated)

### Step A — Detect /export artifacts in repo root (automated)
Claude Code MUST execute:
- ls -1
- git status -sb

Identify only known /export patterns (do NOT use "all *.txt"):
- conversation-*.txt
- *-task-*.txt
- *-claude-code-*.txt

If any matches exist:
1) Propose running /archive-exports.
2) Run /archive-exports after user confirmation.
3) Re-run the root checks above to confirm export artifacts are gone.

Fallback (only if commands cannot run):
Ask user to run:
- ls -1
- git status -sb

### Step B — Draft Session Closure Log (generate content here, automated)

#### B0) Short-circuit: closure already done? (automated)

Claude Code MUST execute before any other Step B work:

```bash
# Step 1: get today's date (separate Bash call — no $() substitution)
date -u +%Y_%m_%d
```

```bash
# Step 2: check for existing closure log (use literal date from step 1)
ls docs/state/session_closure_log_<YYYY_MM_DD>_v_*.md 2>/dev/null || true
git status -sb
```

**Note:** Execute `date` as a SEPARATE Bash call first, then use the literal result in the `ls` command. NEVER use `$(date ...)` inline.

**Decision rule:**
- If at least one `session_closure_log_<today>_v_*.md` exists, AND
- `git status -sb` is clean (output is exactly `## <branch>`, no other lines)

Then: output `"Closure log already current for <today>. Skipping draft."` and proceed directly to **Step C**. Do not execute B1–B3.

Otherwise: continue with B1 as normal.

#### B1) Determine destination path and next version (automated)
Claude Code MUST execute (prefer this order):
- test -d docs/state && echo "docs/state: OK" || echo "docs/state: MISSING"
- ls -la docs 2>/dev/null || true
- find docs -maxdepth 3 -type d -name state -print 2>/dev/null || true
- ls -1 docs/state 2>/dev/null | grep -E '^session_closure_log_[0-9]{4}_[0-9]{2}_[0-9]{2}_v_[0-9]+_[0-9]+\.md$' || true

Naming rule:
- session_closure_log_YYYY_MM_DD_v_1_0.md (date = user's local date)
- if same-date log already exists, increment MINOR: v_1_1, v_1_2, ...

If user local date is unknown, Claude Code SHOULD infer from environment if available; otherwise request it as a single fact from user (one line).

Fallback (only if path discovery commands cannot run):
Ask user to run:
- ls -la docs
- find docs -maxdepth 3 -type d -name state -print
- ls -1 docs/state | grep -E '^session_closure_log_'

#### B2) Gather closure facts (automated)
Claude Code MUST execute:
- git status -sb
- git diff --name-status
- git diff --stat
Optionally:
- git log -n 12 --oneline

Fallback (only if git commands cannot run):
Ask user to run the same commands and paste outputs.

#### B3) Produce the draft content (mandatory sections)
Generate a markdown draft with mandatory sections:

1. Meta (date, version, branch, scope)
2. Цель сессии
3. Что было сделано (по шагам)
4. Изменения (code / docs / server)
5. Принятые решения
6. Риски / проблемы
7. Открытые вопросы
8. Точка остановки
9. Ссылки на актуальные документы
10. CHANGELOG

Rules:
- Each bullet must be verifiable (command -> result -> fact).
- If a section has no evidence, state "Нет данных" (do not invent).
- Output must include: suggested file path + full markdown body (ready to save).

### Step C — Final checks & reminders (automated)
Claude Code MUST execute:
- git status -sb
- git diff --name-only
- find . -maxdepth 1 -type f \( -name "conversation-*.txt" -o -name "*-task-*.txt" -o -name "*-claude-code-*.txt" \) -print

Remind:
- NEVER git-add or commit anything under _audit/**
- _audit/** must remain gitignored

### Step D — MEMORY.md update (automated)

Read tool:
- Auto memory: `/home/dmitry/.claude/projects/-opt-projects-pdf-extractor/memory/MEMORY.md`

Update:
- "Current Status": mark completed items, set pending correctly
- "Next Steps": reflect what was done, what comes next
- Add new patterns/lessons from this session (if any)
- Remove outdated entries

Keep under 200 lines. Facts only.

## Output rules
- Facts only; no assumptions about executed commands.
- Never claim exports were archived unless the post-check shows none in repo root.
- Never propose destructive commands.
- Stop if any action would touch paths outside `_audit/claude_code/` or `.claude/` without explicit permission.
