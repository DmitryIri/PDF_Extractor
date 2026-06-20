# active_handoff.md — Shared Live Handoff Surface for `pdf-extractor`

Use this file only for real unfinished live work that needs pickup by another
actor or a later session.

This file is:
- shared between agents
- mutable by design
- intentionally short

This file is not:
- a session log
- a project summary
- an archive

Lifecycle:
- absent or effectively empty when no live handoff exists
- active when there is unfinished transfer state
- cleared or reset when the handoff is no longer needed

---

## Update Protocol v1

Purpose:
This file exists only for real unfinished shared state that must be safely picked
up by another actor or a later session.

Who updates:
Only the current owner of the task may update this file.

Allowed owner values:
- `Claude Code`
- `Codex`
- `User`
- `none`

Update only when:
- owner changes;
- work is paused mid-task and needs pickup later;
- the next best step changed in a way that matters for pickup;
- new critical blockers appeared.

Do not update when:
- ending a session just for routine;
- the task is complete;
- the state is already fully reflected in canonical/shared artifacts;
- the residue is only agent-local process knowledge.

Format rules:
- keep the file short and factual;
- `current state` = 1-3 factual lines max;
- `next` = exactly one best next step;
- `refs` = 1-3 key references.

When handoff is no longer needed:
reset the file to neutral state instead of deleting it.

Priority rule:
- `docs/**` = project truth
- `session_closure_log_*` = historical session truth
- `active_handoff.md` = live transfer state only

`active_handoff.md` does not override project truth.

Single-owner rule:
One active handoff task has one owner.
If owner changes, reflect it in the file.

Routing rule:
1. Shared unfinished state -> update `active_handoff.md`
2. Agent-local operating residue -> write to `.codex/*` or `.claude/*`

---

task: none
why handoff exists: none
owner: none
current state: none
next: none
blockers: none
refs: none
last_updated: 2026-04-21 by Codex
