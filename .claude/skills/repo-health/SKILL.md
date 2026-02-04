---
name: repo-health
description: Pre-work sanity check — git status, export scan, _audit hygiene, venv, settings drift. Read-only, no auto-fixes.
disable-model-invocation: true
allowed-tools:
  - Bash
---

# repo-health

## Purpose

Single read-only check before starting work or before committing.
Detects common issues early. Never auto-fixes anything — reports only.

Designed to be invoked:
- at the start of any session (after bootstrap)
- before any git commit (subsumes ops_router T3 pre-checks)

## Checks (executed in order)

### 1. Git status

```bash
git status -sb
```

- Clean (`## <branch>` only) → OK
- Otherwise → list all modified / untracked entries

### 2. Export artifact scan

Scan repo root for known /export output patterns only:

```bash
find . -maxdepth 1 -type f \( \
  -name "conversation-*.txt" \
  -o -name "*-task-*.txt" \
  -o -name "*-claude-code-*.txt" \
  -o -name "20??-??-??-*.txt" \
\) -print
```

- Any matches → WARN: propose `/archive-exports`
- None → OK

### 3. _audit staging check

```bash
git diff --cached --name-only | grep ^_audit/ || true
```

- Any _audit files in index → ERROR: must unstage before commit
- None → OK

### 4. Venv / runtime Python availability

```bash
test -d .venv && echo ".venv: present" || echo ".venv: missing"
test -x /srv/pdf-extractor/venv/bin/python && echo "runtime python: accessible" || echo "runtime python: not accessible"
```

Reports presence only. Does not execute Python.

### 5. settings.local.json drift

```bash
python3 -c "
import json, sys
try:
    a = json.load(open('.claude/settings.local.json'))['permissions']['allow']
    n = len(a)
    print(f'settings.local.json entries: {n}')
    if n > 60:
        print('WARN: drift detected (>{60}). Consider sanitization.')
    else:
        print('OK')
except Exception as e:
    print(f'settings.local.json: {e}')
" 2>/dev/null || echo "settings.local.json: not found or unreadable"
```

- Threshold: >60 entries → WARN
- ≤60 → OK
- File missing → note (acceptable if session has no local overrides)

## Output format

Single summary block, always in this shape:

```
=== repo-health ===
[1] git status:        OK | <dirty entries>
[2] export artifacts:  OK | WARN → /archive-exports
[3] _audit staging:    OK | ERROR → unstage <files>
[4] venv:              .venv: present | runtime: accessible
[5] settings drift:    OK | WARN: N entries
```

## Rules

- Read-only: zero file writes, zero auto-fixes, zero deletions.
- If any ERROR: block work and require resolution before continuing.
- If any WARN: surface to user, suggest appropriate skill or action.
- Never claim OK on a check that was not actually executed.

## Version

**Version**: 1.0
**Date**: 2026-02-04
