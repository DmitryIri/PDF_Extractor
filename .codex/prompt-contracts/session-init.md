# Session Init Prompt Contract — `pdf-extractor`

## Purpose

Canonical prompt contract for starting a new Codex session in `pdf-extractor`.

This is not a runnable slash-command.
It is a reusable prompt artifact for consistent Codex bootstrap.

---

## Canonical Prompt

```text
Новая сессия в pdf-extractor.

Сначала примени global user context, затем выполни project bootstrap по AGENTS.md.
Если для задачи релевантны Codex-local operating artifacts, прочитай также .codex/README.md.
Если есть unfinished live work, проверь также active_handoff.md.

После bootstrap:
1. дай короткий kickoff summary,
2. перечисли open items из latest closure log,
3. предложи next step,
4. не начинай изменения до моей следующей команды.
```

---

## Expected Bootstrap Order

1. Global user context
2. `AGENTS.md`
3. `README.md`
4. `CLAUDE.md`
5. `.codex/README.md` when Codex-local operating artifacts are relevant
6. `docs/governance/project_files_index.md`
7. latest `docs/state/session_closure_log_*.md`
8. `active_handoff.md` if there is unfinished live work
9. only then task-relevant design / policy / state docs

---

## Expected Output

Expected kickoff output should contain:

- short project status
- open items from latest closure log
- proposed next step
- brief note about what bootstrap artifacts were read

Do not start implementation unless the user explicitly requests it.
