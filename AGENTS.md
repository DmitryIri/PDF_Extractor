# AGENTS.md — Codex Operating Entry for `pdf-extractor`

## Purpose

This file is the project-local Codex bootstrap for `pdf-extractor`.
It defines how Codex should recover context and operate safely here without
duplicating the global `~/.codex` layer.

Use this file as the Codex entrypoint for repo-local work.

---

## Layer Model

Keep these layers separate:

1. Global layer
   `~/.codex/AGENTS.md`, global user profile, shared behavior defaults.
   Not duplicated in this repo.

2. Project layer
   Shared project truth in `README.md`, `CLAUDE.md`, versioned docs under `docs/`,
   and other canonical project artifacts.

3. Claude operating layer
   `CLAUDE.md` + `.claude/**`.

4. Codex local operating layer
   `AGENTS.md` + `.codex/**`.
   `AGENTS.md` is the entrypoint; `.codex/` is the expandable Codex-local
   operating namespace.

5. Shared session / handoff layer
   Historical session memory lives in `docs/state/session_closure_log_*.md`.
   Live unfinished task-transfer state lives in `active_handoff.md`.
   Neither belongs to `.codex/`.

---

## Repository Facts

- Project purpose: deterministic pipeline that splits journal issue PDFs into
  article PDFs with verified metadata and reproducible outputs.
- Code lives in `/opt/projects/pdf-extractor/`; runtime artifacts live in `/srv/pdf-extractor/`.
- Shared documentation is stored under `docs/`.
- Canonical doc registry is `docs/governance/project_files_index.md`.
- `docs/state/session_closure_log_*.md` is the canonical in-repo session history.
- `active_handoff.md` is the shared live handoff surface for unfinished work that
  needs pickup by another actor or a later session.
- `CLAUDE.md` is the Claude Code project entrypoint and points to:
  `session-init-pdf_extractor` / `session-close-pdf_extractor`.
- `.claude/` is Claude Code operating infrastructure, not Codex workspace.
- `.codex/` is the Codex-local operating namespace for prompt contracts and
  other Codex-specific reusable artifacts.

---

## Read First

When Codex enters this repo, bootstrap in this order:

1. Read `AGENTS.md` first.
2. Read `README.md` for project purpose and system shape.
3. Read `CLAUDE.md` for source-of-truth map, invariants, and workflow boundaries.
4. Read `.codex/README.md` if Codex-local operating artifacts are relevant.
5. Read `docs/governance/project_files_index.md`.
6. Read the latest `docs/state/session_closure_log_*.md`.
7. Read `active_handoff.md` if there is live unfinished work or a real handoff situation.
8. Read only the task-relevant docs after that:
   `docs/design/*`, `docs/policies/*`, `docs/state/project_summary_v_*.md`,
   or other directly relevant files.

Default assumption after bootstrap:
- project truth lives in canonical docs;
- latest session state lives in the latest closure log;
- live unfinished transfer state, if any, lives in `active_handoff.md`;
- runtime artifacts under `/srv/` are not source of truth by themselves;
- missing repo-local Codex instructions should not be invented unless needed.

---

## Codex Session Start

Canonical session-start prompt now lives in:

- `.codex/prompt-contracts/session-init.md`

Use this prompt at the beginning of a new Codex session in `pdf-extractor`:

```text
Новая сессия в pdf-extractor.
Сначала прочитай AGENTS.md и выполни bootstrap по зафиксированному протоколу.
Потом:
1. дай короткий kickoff summary,
2. перечисли open items из latest closure log,
3. предложи next step,
4. не начинай изменения до моей следующей команды.
```

Expected bootstrap path:

1. `AGENTS.md`
2. `README.md`
3. `CLAUDE.md`
4. `.codex/README.md` if Codex-local operating artifacts are relevant
5. `docs/governance/project_files_index.md`
6. latest `docs/state/session_closure_log_*.md`
7. `active_handoff.md` if there is live unfinished work
8. only then task-relevant design / policy / state docs

This section is a user ritual, not a runnable slash-command.

---

## Authority Boundaries

Codex should treat these areas differently:

- `docs/**`
  Shared project truth and session history. Do not edit by default.
  Edit only when the user explicitly asks for documentation or governance work.

- `active_handoff.md`
  Shared live handoff artifact. Not Codex-local.
  Read when unfinished work may need pickup across sessions or agents.
  Update only when there is real live transfer state.

- `.claude/**`
  Claude Code operating layer. Do not edit by default.
  Edit only when the task is specifically about Claude Code infrastructure or the
  user explicitly requests it.

- `/srv/pdf-extractor/**`
  Runtime artifacts, inputs, outputs, and operational state.
  Do not modify by default without explicit task scope.

- `_audit/**`
  Auxiliary artifacts. Do not rely on it as source of truth unless the user explicitly asks.
  Never propose committing it.

- `README.md`, `AGENTS.md`, `.codex/**`
  Repo entrypoint files. Safe to update when the task is specifically about repo
  bootstrap, onboarding, or Codex operating boundaries.

If a requested change affects determinism, exit codes, contracts, or T = L = E,
verify against canonical docs before editing code.

---

## Operating Rules For Codex

- Prefer minimal, local changes over framework-building.
- Reuse existing repo patterns instead of creating parallel Codex-only systems.
- Do not duplicate global `~/.codex` instructions inside the repo.
- Do not invent a Codex-specific memory system when the project index and closure logs
  already provide bootstrap context.
- Keep Codex context narrow: read only the files needed for the current task.
- If project docs and chat context disagree, trust repo artifacts.
- Separate confirmed facts, inference, and unknowns when they matter.
- Respect the code/runtime split: `/opt/projects/pdf-extractor/` is code,
  `/srv/pdf-extractor/` is runtime and artifacts.

---

## Session And Handoff Reuse

Codex should reuse the existing session model instead of creating a new one:

- For historical context: read the latest `docs/state/session_closure_log_*.md`.
- For live unfinished shared task-transfer state: read `active_handoff.md` when relevant.
- For current project document inventory: read `docs/governance/project_files_index.md`.
- For Codex-local operating conventions and reusable prompts: inspect `.codex/**`
  when relevant to the task.
- For Claude-specific workflow references: inspect `CLAUDE.md` and `.claude/skills/`
  only when relevant to the task.

Codex does not need runnable repo-local `/session-init` or `/session-close` clones.
Instead, use prompt contracts under `.codex/` plus shared project artifacts.
`.codex/` does not own shared handoff state; `active_handoff.md` does.

## Shared Handoff Rule

`active_handoff.md` is the shared live handoff artifact for unfinished work.

Rules:

- update it only for real unfinished shared state;
- update it only by the current owner of the task;
- do not use it for session reports or agent-local notes;
- if the residue is Codex-local only, store it in `.codex/*`, not in `active_handoff.md`;
- if the task is complete and reflected in shared artifacts, clear `active_handoff.md`
  to neutral state.

Priority:

- `docs/**` = project truth
- session closure logs = historical session memory
- `active_handoff.md` = live transfer state only

---

## Minimal Write Scope

Unless the user explicitly asks otherwise, Codex should assume its safe default
write scope in this repo is:

- code, tests, and tooling files directly related to the task;
- repo-local Codex bootstrap files such as `AGENTS.md` and `.codex/**`.

Out of default scope:

- broad doc rewrites in `docs/**`;
- `.claude/**` refactors;
- runtime modifications under `/srv/pdf-extractor/**`;
- replacing existing session or handoff systems with Codex-specific ones.

---

## When This File Is Not Enough

Prefer keeping Codex-local artifacts under `.codex/` when they are:

- prompt contracts;
- audit playbooks;
- bootstrap notes;
- session start or session close templates;
- other Codex-specific operating helpers that are not shared project truth.

Do not use `.codex/` for:

- duplicated project truth from `docs/**`;
- copies of `README.md` or `CLAUDE.md`;
- fake runnable skills or agents without runtime support;
- a second project memory system.

Use `active_handoff.md` instead when there is real shared unfinished transfer state.
