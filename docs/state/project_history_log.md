# Project History Log

**Проект:** PDF Extractor  
**Статус:** Canonical  
**Назначение:** Кумулятивная история ключевых событий и вех проекта.

---

## 2026-01-22
- **Audit exports infrastructure established** (commit 34344ad):
  - Создана `.claude/rules/audit_exports.md` — canonical policy для Claude Code /export artifacts
  - Создан `.claude/skills/archive-exports/SKILL.md` — reusable skill для архивации экспортов
  - Создан `.claude/settings.json` — project-level permissions (git-tracked)
  - Определены канонические пути: `_audit/claude_code/exports/`, `_audit/claude_code/reports/`
- **TechSpec v_2_5 committed** (commit 5c4abd3):
  - Добавлена спецификация stdin envelope + stdout/stderr contract
  - Формализована typography-based detection (PRIMARY SIGNAL)
  - Документирована rich article_starts schema
- **Documentation alignment completed** (commit 71315ff):
  - Plan v_2_3 обновлён: все ссылки на TechSpec v_2_4 заменены на v_2_5
  - BoundaryDetector v_1_1 создан как minimal patch от v_1_0 (синхронизация с TechSpec v_2_5)
- **Verification evidence generated** (не закоммитено, в `_audit/claude_code/reports/`):
  - Verification artifacts для BoundaryDetector v_1_1 claims (vs TechSpec + code)
  - TechSpec v_2_4 → v_2_5 full patch + diffstat
  - SHA256 manifests для аудита
- Project Summary v_2_8 создан
- **Status**: Все коммиты local-only (branch: feature/phase-2-core-autonomous), push не выполнялся

## 2026-01-14
- Инициализирован `project_history_log.md` как канонический State-артефакт.
- Зафиксирован и размещён канонический `PROJECT_FILES_INDEX v_1_2`.
- Документ доведён до Claude-ready состояния (физические пути + сценарий Claude Code Bootstrap).
- Снят блокер для начала работы в Claude Code.

