# Project History Log

**Проект:** PDF Extractor  
**Статус:** Canonical  
**Назначение:** Кумулятивная история ключевых событий и вех проекта.

---

## 2026-01-22
- **GitHub remote configured (origin), sync deferred until Phase 2 completion**: GitHub repo `DmitryIri/PDF_Extractor` will be stitched/merged after Phase 2; current SoT remains `/opt/projects/pdf-extractor`.
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

- **Session closure logs synced into repo** (commit c799feb):
  - Добавлены отсутствующие `session_closure_log_*.md` в `docs/state/` (итого 16 файлов)
- **Plan v_2_4 created to resolve doc-mismatch** (commits 3a43ea9, b7da1f7):
  - Acceptance: `confidence == 1.0` (binary match) + rich `article_starts` objects
  - Исправлены заголовок и canonical marker внутри `pdf_extractor_plan_v_2_4.md`
- **Project Summary pointers updated to Plan v_2_4** (commit c2ee87c):
  - `project_summary_v_2_8.md` теперь указывает Canonical Plan = v_2_4

## 2026-01-14
- Инициализирован `project_history_log.md` как канонический State-артефакт.
- Зафиксирован и размещён канонический `PROJECT_FILES_INDEX v_1_2`.
- Документ доведён до Claude-ready состояния (физические пути + сценарий Claude Code Bootstrap).
- Снят блокер для начала работы в Claude Code.

