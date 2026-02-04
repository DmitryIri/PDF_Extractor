# Ops Router v_1_0 — Skill Routing & Reminders (Canonical)

## Purpose
Ensure Claude Code consistently applies project workflows without the user needing to remember skills/rules.

## Global rule
If a situation matches a trigger below, Claude Code MUST propose the corresponding skill before continuing.

## Triggers → Required action

### T1. Root contains /export artifacts
Trigger condition (any of):
- repo root has files matching known /export patterns (e.g., conversation-*.txt, *-task-*.txt)
- git status shows untracked export artifacts in root

Required action:
1) Propose running /archive-exports (do not delete anything automatically)
2) After user confirmation, run /archive-exports
3) Re-check root: no export artifacts remain

### T2. Session closure requested OR user indicates end-of-work
Trigger condition:
- user says "Завершение сессии" or similar
- user asks to prepare closure/summary/hand-off

Required action order:
1) Check T1 and resolve via /archive-exports if needed
2) Run /session-closure-log to draft session closure doc(s)
3) Remind: _audit/** must remain untracked (gitignored)

### T3. Before proposing git commit
Trigger condition:
- user asks to commit
- Claude Code suggests committing

Required action:
1) Check T1; if root has export artifacts → STOP and propose /archive-exports
2) Ensure no files under _audit/** are staged or suggested for commit

## Non-goals
- Does not auto-run destructive actions
- Does not modify _audit/snapshot_* folders
- Does not change /export behavior (it writes to root)

## Stop condition
If any suggested command touches paths outside:
- _audit/claude_code/
- .claude/
then STOP and request explicit permission.
