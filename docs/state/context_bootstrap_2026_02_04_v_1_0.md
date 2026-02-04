# Context Bootstrap — 2026-02-04

**Статус:** Canonical
**Версия:** v_1_0
**Назначение:** Быстрое восстановление контекста для следующей сессии после housekeeping.

---

## 1. Текущее состояние репозитория

- **Ветка:** main
- **Tree:** clean (no untracked, no modified)
- **Последние 3 коммита:**
  - `f0804ca` — chore(settings): add git show + git check-ignore to project allowlist
  - `44e3843` — chore(gitignore): ignore Claude skill .bak artifacts
  - `df35880` — chore(claude): version skills/rules + add sha256 gate to archive-exports

---

## 2. Что закрыто (housekeeping — полностью)

| Задача | Результат | Доказательство |
|--------|-----------|----------------|
| /archive-exports | 5 файлов архивированы, root clean | sha256sum -c 5/5 OK |
| archive-exports gate bugfix | SKILL.md v_1_1, step 6 added | dry-run 5/5 OK |
| .claude/* versioning | 5 файлов скоммитены | SHA df35880 |
| .gitignore .bak pattern | rule added, 2 .bak deleted | SHA 44e3843 |
| settings.json allowlist | +git show, +git check-ignore | SHA f0804ca |
| settings.local.json sanitize | 93 → 43 entries, backup deleted | JSON valid, stale = 0 |

---

## 3. Для следующей сессии (bootstrap checklist)

- [ ] Прочитать `CLAUDE.md` — project invariants и pipeline structure.
- [ ] `git status -sb` — должен быть clean.
- [ ] Ближайшие задачи — Phase 3: UI/DB bootstrap (см. `docs/governance/task_specs/task_spec_phase_3_ui_db_bootstrap_v_1_0.md`).
- [ ] Каноническая документация: TechSpec v_2_6, BoundaryDetector v_1_2, filename_generation_policy v_1_1.
- [ ] Runtime python: `/srv/pdf-extractor/venv/bin/python` (PYTHONPATH=/opt/projects/pdf-extractor).

---

## 4. Open questions

- **Allowlist tier policy:** рассмотреть формализацию "read-only" vs "mutation" tiers в settings.json для снижения ручного управления permissions.
- **settings.local.json drift:** при накоплении новых one-off entries — периодическая санитизация (порог: >60 entries).

---

## 5. CHANGELOG

- **v_1_0 — 2026-02-04** — Initial context bootstrap. Housekeeping session outcomes recorded. Коммиты: df35880, 44e3843, f0804ca.
