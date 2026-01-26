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

## 2026-01-23
- **Phase 2.5 BoundaryDetector completed** (commit cf75aa9):
  - Golden test artifacts committed: `mg_2025_12_anchors.json` (18,184 anchors), `mg_2025_12_boundaries.json` (28 article_starts + boundary_ranges), `mg_2025_12_article_starts.json` (canonical reference)
  - Verifier script added: `scripts/verify_boundary_detector_golden.py` — validates article_starts against golden reference, checks confidence == 1.0, verifies boundary_ranges invariants
  - Determinism proven: 2 runs → identical output (10,507 bytes)
- **MetadataExtractor stdout/stderr contract fix** (commit cbc625c):
  - Changed JSON emission to use `os.write(1, json_bytes)` for explicit fd1 output per TechSpec v_2_5
  - Fixes contract violation where JSON was emitted to stderr
  - Tested: anchors.json 5,049,995 bytes (18,184 anchors, 156 pages), stderr 0 bytes, exit_code 0
- **.gitignore exception for golden_tests JSON** (commit bd169c6):
  - Added `!golden_tests/**/*.json` exception to allow tracking golden test artifacts
  - Prevents accidental tracking of runtime artifacts while enabling canonical references
- **docs/design hygiene completed** (commit 28d168d):
  - Archived non-canonical design artifacts (git mv, history preserved):
    - `pdf_extractor_techspec_v_2_4.md` → `docs/_archive/techspec/` (superseded by v_2_5)
    - `pdf_extractor_boundary_detector_v_1_0.md` → `docs/_archive/design/` (superseded by v_1_1)
  - Updated references: CLAUDE.md primary documentation pointer (v_2_4 → v_2_5), boundary_detector_v_1_1.md previous version link
  - Canonical KEEP list: TechSpec v_2_5, Plan v_2_4, BoundaryDetector v_1_1
- **Phase 2.6 Splitter completed (Plan v_2_4 §5.6, Шаг 2.5: lines 157-169)** (commits 3bbf4a1, 93a69ec):
  - Physical PDF splitting by boundary ranges from BoundaryDetector
  - Canonical PDF: `/srv/pdf-extractor/tmp/Mg_2025-12.pdf` (~8.3 MB; 8345036 bytes)
  - Article PDFs created: 28 (pages 5-156)
  - Determinism verified: SHA256 hashes stable across 2 independent runs
  - Verifier script: `scripts/verify_splitter_golden.py` — validates PDFs against golden boundaries
  - Golden artifact: `golden_tests/mg_2025_12_splitter_output.json` (8,765 bytes)
  - Export archived: `_audit/claude_code/exports/2026_01_23__10_15_32/2026-01-23-bootstrap-only-do-not-run-any-long-commands.txt` (SHA256: 7a8eb86a7221bab6125832fd5cd53131da82eae03ccbd79bc607fa91d25a8074)
- **Phase 2.6 MetadataVerifier completed** (commit 6d67412):
  - Manifest verification + enrichment для OutputBuilder readiness
  - Validates: required fields, page ranges, file existence, naming rules
  - Enriches: journal_code, issue_prefix, expected_filename, splitter_output metadata (sha256, bytes)
  - Deterministic output: sort_keys, stable article ordering
  - Test fixture: `tests/fixtures/metadata_verifier_input_minimal.json` (3 articles)
- **Status**: Все коммиты local-only (branch: feature/phase-2-core-autonomous), push не выполнялся

## 2026-01-26
- **Phase 2.7 OutputBuilder completed (Plan v_2_4 §5.8, Шаг 2.7)**:
  - Implemented `agents/output_builder/builder.py` (v_1_0.0)
  - Stdin/stdout envelope contract per TechSpec v_2_5
  - Atomic export: сборка в `{export_id}.tmp/` → atomic rename в `{export_id}/`
  - Export structure: `/srv/pdf-extractor/exports/{JournalCode}/{YYYY}/{IssuePrefix}/exports/{export_id}/`
    - `articles/` — Article PDFs с canonical naming: `{IssuePrefix}_{PPP-PPP}_{FirstAuthorSurname}.pdf`
    - `manifest/export_manifest.json` — Export metadata (journal, issue, articles list, timestamps)
    - `checksums.sha256` — SHA256 checksums для всех article PDFs (SHA256SUMS format)
    - `README.md` — Human-readable export documentation с verification instructions
  - Exit codes: 0=success, 10=invalid_input, 40=build_failed, 50=internal_error
  - Naming rule enforcement: 3-digit zero-padded page numbers per session_closure_log_2026_01_23_v_1_2.md §3.1
  - Deterministic export_id generation: `YYYY_MM_DD__HH_MM_SS` (UTC timestamp)
- **OutputBuilder testing**:
  - Unit tests: `tests/test_output_builder.sh` (5 тестов: 1 happy path + 4 negative)
  - Test coverage: missing fields, invalid formats, non-existent source PDFs
  - Integration test: MetadataVerifier → OutputBuilder pipeline успешен (3 статьи экспортированы)
  - Checksums validated: `sha256sum -c checksums.sha256` → all OK
- **Test fixtures**:
  - Added `tests/fixtures/output_builder_input_minimal.json` (2 articles minimal example)
- **Documentation updates**:
  - Created Project Summary v_2_9 (from v_2_8)
  - Updated project_history_log.md
  - Documented decision D4: Canonical Export Structure (FS-only, no DB/UI)
  - Documented known limitation Q1: source of `first_author_surname` (между Splitter и MetadataVerifier)
- **Активная фаза:** Phase 2.7 → Phase 2.8 (OutputValidator next)
- **Status**: Все коммиты local-only (branch: feature/phase-2-core-autonomous), push не выполнялся

## 2026-01-14
- Инициализирован `project_history_log.md` как канонический State-артефакт.
- Зафиксирован и размещён канонический `PROJECT_FILES_INDEX v_1_2`.
- Документ доведён до Claude-ready состояния (физические пути + сценарий Claude Code Bootstrap).
- Снят блокер для начала работы в Claude Code.

