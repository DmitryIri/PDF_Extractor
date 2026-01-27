---
name: archive-exports
description: Archive Claude /export artifacts from repo root to _audit/claude_code/exports with sha256 manifest
disable-model-invocation: true
allowed-tools:
  - Bash
  - Read
  - Glob
  - Grep
---

# Archive Exports Skill

## Purpose

Archives Claude Code `/export` artifacts from the repository root to canonical audit locations with deterministic session tracking and sha256 checksums.

## Behavior

This skill safely copies export artifacts to session-specific folders and generates audit manifests without modifying source files (unless user explicitly confirms deletion).

## Workflow

### 1. Ensure directory structure exists

```bash
mkdir -p _audit/claude_code/exports _audit/claude_code/reports
```

### 2. Determine session ID with deterministic fallback

```bash
SESSION_ID="${CLAUDE_SESSION_ID:-$(date -u +%Y_%m_%d__%H_%M_%S)}"
DEST_DIR="_audit/claude_code/exports/${SESSION_ID}"
mkdir -p "$DEST_DIR"
```

**Fallback logic**:
- If `CLAUDE_SESSION_ID` is set: use it
- Otherwise: use UTC timestamp `YYYY_MM_DD__HH_MM_SS`

### 3. Select files to archive

**Default selection (no arguments)**:

Only strict patterns for known /export outputs:
```bash
conversation-*.txt
20??-??-??-task-*-mode*.txt
20??-??-??-pdf-extractor-facts*.txt
20??-??-??-you-are-in-doc-editing-mode*.txt
```

**With arguments**:

Use explicit pattern from `$ARGUMENTS`:
```bash
# Example: /archive-exports 2026-01-22-*.txt
```

**Never**:
- Use wildcard "all *.txt" without explicit user specification
- Select files under `_audit/` or `.git/`
- Select `.env` or `secrets/**`

### 4. Copy with metadata preservation

```bash
for file in <selected_files>; do
  cp -a "$file" "$DEST_DIR/"
done
```

Uses `cp -a` to preserve:
- Timestamps (mtime, atime)
- Permissions
- Ownership (where possible)

### 5. Generate sha256 manifest (anchored from repo root)

**CRITICAL**: Do NOT use `cd` - anchor path from repo root to avoid relative path bugs.

```bash
sha256sum "$DEST_DIR/"* > "_audit/claude_code/reports/sha256_exports_${SESSION_ID}.txt"
```

**Why anchored path**:
- Avoids `../../` relative path errors
- Deterministic regardless of working directory
- Easier to audit (absolute paths in manifest)

### 6. Show evidence

```bash
echo "=== Archived files ==="
ls -la "$DEST_DIR"

echo ""
echo "=== SHA256 manifest (first 40 lines) ==="
sed -n '1,40p' "_audit/claude_code/reports/sha256_exports_${SESSION_ID}.txt"
```

### 7. List remaining root files and request confirmation

After successful copy:

1. List files in root that still match the selection patterns
2. Ask user: "Delete these files from root? (y/n)"
3. **Do NOT auto-delete** - wait for explicit confirmation
4. If user confirms: `rm <files>`
5. If user declines: leave files in place

**Safety**: No automatic deletion. User must explicitly confirm.

## Optional: Dry-Run Mode

If `--dry-run` is in arguments:

1. Show which files would be selected
2. Show target directory path
3. Do NOT copy files
4. Do NOT generate manifest
5. Exit with message: "Dry-run complete. No files modified."

## Exit Conditions

**Success**:
- Files copied successfully
- Manifest generated with sha256 checksums
- Evidence shown to user
- Exit code: 0

**Failure scenarios**:
- Directory creation failed → Exit with error
- No files matched patterns → Exit with warning (not error)
- Copy failed → Exit with error
- sha256sum failed → Exit with error

## Safety Constraints

### Absolute prohibitions

- **NO automatic deletion** of source files (user must confirm)
- **NO modification** of `_audit/snapshot_*` folders
- **NO git operations** on `_audit/**` contents
- **NO processing** of `.env` or `secrets/**`
- **NO destructive operations** without user confirmation

### Path boundaries

All operations confined to:
- Read from: `.` (repo root, filtered by strict patterns)
- Write to: `_audit/claude_code/{exports,reports}`

If any operation would touch paths outside these boundaries:
- STOP immediately
- Report to user
- Request explicit permission

## Usage Examples

### Example 1: Archive all known /export patterns (default)

```bash
/archive-exports
```

**Result**:
- Matches: `conversation-*.txt`, `20??-??-??-task-*.txt`, etc.
- Copies to: `_audit/claude_code/exports/${SESSION_ID}/`
- Generates: `_audit/claude_code/reports/sha256_exports_${SESSION_ID}.txt`

### Example 2: Archive specific files (explicit)

```bash
/archive-exports 2026-01-22-*.txt
```

**Result**:
- Matches only files starting with `2026-01-22-` and ending with `.txt`

### Example 3: Dry-run (preview without copying)

```bash
/archive-exports --dry-run
```

**Result**:
- Shows which files would be selected
- No files copied
- No manifest generated

## Implementation Notes

### Session ID format

- With `CLAUDE_SESSION_ID`: Use as-is (typically UUID or similar)
- Without: `YYYY_MM_DD__HH_MM_SS` in UTC
- Ensures folder names are:
  - Deterministic
  - Sortable chronologically
  - Unique (within 1-second resolution)

### sha256 manifest format

```
<checksum>  <relative_path_from_repo_root>
```

Example:
```
a1b2c3...  _audit/claude_code/exports/2026_01_22__15_52_30/conversation-2026-01-15.txt
d4e5f6...  _audit/claude_code/exports/2026_01_22__15_52_30/2026-01-21-task-default-mode-server.txt
```

### Error handling

- File not found: Skip with warning
- Permission denied: Report error and exit
- Disk full: Report error and exit
- Invalid pattern: Report error and exit

---

**Version**: 1.0
**Date**: 2026-01-22
**Tested**: No (awaiting first run)
