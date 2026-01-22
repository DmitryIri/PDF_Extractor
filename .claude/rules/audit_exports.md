# Audit Exports - Project Memory Rule

## Definitions

- **Exports**: Primary source artifacts created by Claude Code `/export` command
- **Reports**: Derived audit manifests (sha256 checksums, metadata)

## Canonical Paths

- Primary sources: `_audit/claude_code/exports/`
- Derived reports: `_audit/claude_code/reports/`

## Policy

### 1. Never keep exports in repo root after session

Export artifacts (*.txt files from /export) MUST be moved to canonical locations before session ends.

### 2. Archive using /archive-exports skill

When untracked export artifacts appear in root:
- Run `/archive-exports` to copy them to session-specific folder
- Generate sha256 manifest in reports/
- Review list of remaining files before deletion

### 3. Git tracking rules

- NEVER git-add or commit anything under `_audit/**`
- `_audit/**` is gitignored at project level
- Export artifacts should not pollute root directory status

### 4. Audit trail requirements

- All archived exports must have sha256 checksums
- Session ID must be preserved in folder structure: `_audit/claude_code/exports/${SESSION_ID}/`
- Manifests stored in `_audit/claude_code/reports/` for traceability

## Deterministic Workflow

```bash
# User runs /export during session
# → Artifacts created in repo root (*.txt files)

# Before session end:
/archive-exports
# → SESSION_ID="${CLAUDE_SESSION_ID:-$(date -u +%Y_%m_%d__%H_%M_%S)}"
# → Files copied to _audit/claude_code/exports/${SESSION_ID}/
# → sha256 report written to _audit/claude_code/reports/sha256_exports_${SESSION_ID}.txt
# → User confirms deletion of root files
```

**Default file selection** (no arguments):
- Only matches known /export patterns: `*-task-*.txt`, `conversation-*.txt`, etc.
- Never uses wildcard "all *.txt" without explicit user specification

## Stop Condition

If any command touches paths outside `_audit/claude_code/` or `.claude/`:
- STOP immediately
- Report facts to user
- Request explicit permission before proceeding

## Non-Goals

- Does not manage `_audit/snapshot_*` folders (separate concern)
- Does not archive logs, only /export artifacts
- Does not automatically delete root files (requires user confirmation)

---

**Status**: Canonical policy (v1.0)
**Date**: 2026-01-22
