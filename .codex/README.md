# .codex — Codex Local Operating Layer for `pdf-extractor`

## Purpose

`.codex/` stores project-local artifacts that are specific to Codex operation in
this repository.

This directory exists to improve reproducibility and operator UX in a dual-agent
workflow without duplicating shared project truth.

---

## Layer Separation

Keep these layers distinct:

1. Global layer
   `~/.codex/**`, global instructions, user profile, cross-project preferences.

2. Project layer
   `README.md`, `CLAUDE.md`, `docs/**`, and other shared project truth.

3. Codex local operating layer
   `AGENTS.md` plus `.codex/**`.

4. Session / handoff layer
   Shared historical session memory lives in `docs/state/session_closure_log_*.md`.
   Shared live unfinished task-transfer state lives in `active_handoff.md`.
   Codex-local operating residue may live under `.codex/` only when it is not
   project truth and not shared live handoff state.

---

## Relationship With Other Paths

- `AGENTS.md`
  Root Codex entrypoint. Read this first.

- `.claude/**`
  Claude Code operating layer. Not a template to mirror mechanically.

- `docs/**`
  Shared project truth. Do not duplicate it here.

- `active_handoff.md`
  Shared live handoff surface. It is not part of `.codex/` and must not be
  treated as Codex-local state.

---

## Allowed Artifacts

Allowed in `.codex/`:

- prompt contracts
- audit playbooks
- bootstrap notes
- session start templates
- session close templates
- handoff templates
- Codex workflow conventions
- local operating notes
- operator UX helpers

---

## Forbidden Artifacts

Do not store these in `.codex/`:

- duplicated project truth from `docs/**`
- copies of `README.md` or `CLAUDE.md`
- copies of the global user profile
- fake skills, fake agents, or fake hooks with no real runtime support
- a second project memory system
- an alternative project status register
- shared live handoff state
- `active_handoff.md`
- anything that belongs in the shared session closure log

---

## Current Baseline

Current minimal baseline:

- `.codex/README.md`
- `.codex/prompt-contracts/session-init.md`
- `.codex/prompt-contracts/session-close.md`

Add more only when repeated Codex work proves a real need.
`.codex/` must stay thin.
