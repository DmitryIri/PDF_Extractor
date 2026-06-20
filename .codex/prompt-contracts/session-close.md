# Session Close Prompt Contract — `pdf-extractor`

## Purpose

Canonical prompt contract for closing a Codex session in `pdf-extractor`.

This is not a runnable slash-command.
It is a reusable prompt artifact for consistent Codex session wrap-up.

---

## Contract

At session close, Codex should:

1. Verify which project-facing changes are already reflected in shared project artifacts.
2. Route unfinished shared task-transfer state to `active_handoff.md` when another actor
   or later session needs to pick it up.
3. Preserve only Codex-local operating residue in `.codex/**` when it is genuinely useful
   for future Codex sessions.
4. Avoid creating an alternative project closure log or second project memory system.

---

## Routing Decision

### Route A — Shared unfinished task-transfer state

If unfinished state is project-facing and needs pickup by another actor or later
session:

- update or use `active_handoff.md`

### Route B — Codex-only operating residue

If residue is Codex-only operating knowledge:

- store or refine the appropriate `.codex/*` artifact

---

## What May Be Preserved In Codex Local Layer

Allowed Codex-local residue includes:

- improvements to session-start prompts
- notes about better Codex bootstrap in this repo
- reusable audit heuristics
- task-template refinements
- unresolved Codex workflow issues

---

## What Must Not Be Stored As Codex Local Residue

Do not store these as Codex-local session residue:

- live unfinished shared handoff state
- current project state as a second source of truth
- project architecture decisions
- open project tasks that already belong in canonical project artifacts
- anything that should live in `active_handoff.md`
- anything that should be written into `docs/state/session_closure_log_*.md`

`.codex/` must not be used as:

- an alternative live handoff system
- an alternative project state register
- an alternative session history

---

## Canonical Prompt

```text
Завершаем Codex-сессию в pdf-extractor.

Сначала проверь, какие project-facing изменения уже отражены в shared project artifacts.
Не создавай альтернативный project closure log и не дублируй project state.

Если есть unfinished shared state, который должен подхватить другой актор или
следующая сессия, используй `active_handoff.md`.

Если по итогам сессии есть только Codex-local operating residue, относящийся к тому,
как лучше запускать, вести или повторять будущие Codex-сессии в этом repo, сохрани
или уточни его только в `.codex/*`, не смешивая с project state.
```

---

## Expected Result

Expected close-out should separate:

- shared project-facing state
- shared live handoff state
- optional Codex-local operating notes

The third category is allowed only when it does not duplicate shared project truth
or shared live handoff state.
