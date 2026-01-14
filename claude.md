# Claude Code Bootstrap — PDF Extractor

## Scope
Этот файл определяет допустимый порядок действий Claude Code для проекта PDF Extractor.

Claude обязан:
- читать документы строго в указанном порядке;
- не делать предположений вне прочитанных артефактов;
- не выполнять `/init` до выполнения bootstrap.

---

## Mandatory Read Order

Claude Code **обязан** прочитать и интерпретировать следующие документы в указанном порядке:

1. `docs/governance/project_files_index.md`
2. `docs/state/project_summary_vX.Y.md`
3. `docs/state/session_closure_log_YYYY_MM_DD_vX.Y.md` (последний)
4. `docs/state/project_history_log.md`

Без чтения этих файлов **запрещено**:
- выполнять `/init`;
- предлагать архитектурные или кодовые изменения;
- делать выводы о состоянии проекта.

---

## /init Permission

Команда `/init` разрешена **только после**:
- успешного чтения Mandatory Read Order;
- отсутствия противоречий между State-артефактами.

Любое отклонение считается нарушением governance.
