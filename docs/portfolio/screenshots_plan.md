# Screenshots Plan — Upwork Portfolio

3 screenshots for "PDF Extractor" Upwork portfolio project.
Follow this guide step-by-step in VS Code (Remote-SSH to the server).

---

## Screenshot 1 — Project Structure

**Goal:** Show professional, organized Python project with 8 pipeline agents.

**Steps:**
1. Open VS Code, connect Remote-SSH to server.
2. Open folder `/opt/projects/pdf-extractor/`
3. In Explorer panel, expand:
   - `agents/` — expand all 8 subfolders (boundary_detector, input_validator, metadata_extractor, metadata_verifier, output_builder, output_validator, pdf_inspector, splitter)
   - `docs/` — expand `design/`, `policies/`
   - `tests/`, `tools/`, `golden_tests/`
4. Open `README.md` in the editor (center pane).
5. Collapse `.claude/`, `.venv/`, `_audit/`, `ui/` (to keep focus on core pipeline).

**Capture:** Explorer panel (left) + README.md (center). DO NOT show terminal.
**Crop out:** Bottom status bar with username/server IP if visible.

---

## Screenshot 2 — Architecture Diagram

**Goal:** Show the pipeline architecture clearly — 8 agents, data flow, guarantees.

**Steps:**
1. Open file `docs/portfolio/architecture.md` in VS Code.
2. Press `Ctrl+Shift+V` to open **Markdown Preview** side by side.
3. The ASCII pipeline diagram will render clearly.
4. Alternatively, open the file in a plain text editor so the ASCII art is clearly visible with monospace font.

**Capture:** The full pipeline diagram section (from INPUT to OUTPUT).
**What to show:** The 8 boxes with arrows + "Key design decisions" table.
**Crop out:** Anything below the "Material kinds" table if the screenshot gets too long.

---

## Screenshot 3 — Proof / Results

**Goal:** Show real production validation results — numbers, T=L=E, SHA-256.

**Option A (recommended):** Open `docs/state/project_summary_v_2_13.md` and scroll to section "4. Текущее состояние реализации" or "Завершённые milestones". Shows:
- Phase 2 COMPLETED
- Golden test: 29 articles, 100% precision/recall
- 3 production issues validated (T=L=E, sha256)

**Option B:** Open `docs/portfolio/architecture.md`, scroll to the "Production validation" table at the bottom. Clean 4-row table with issue codes, article counts, T=L=E=✅, SHA-256 verified.

**Option C (terminal proof):** In VS Code terminal, run:
```bash
cat golden_tests/mg_2025_12_boundaries.json | python -c "
import json,sys
d=json.load(sys.stdin)
articles=d['data']['article_starts']
print(f'Total article starts detected: {len(articles)}')
print(f'Confidence range: {min(a[\"confidence\"] for a in articles):.1f} – {max(a[\"confidence\"] for a in articles):.1f}')
kinds = {}
for a in articles:
    k = a.get(\"material_kind\",\"?\")
    kinds[k] = kinds.get(k,0)+1
for k,v in sorted(kinds.items()): print(f'  {k}: {v}')
"
```
Expected output:
```
Total article starts detected: 28
Confidence range: 0.7 – 1.0
  contents: 1
  editorial: 1
  research: 26
```

**Capture for Option C:** Terminal output only. DO NOT show the full command if the venv path `/srv/` is visible — crop to just the output lines.

---

## What NOT to show in any screenshot

- Server IP address (crop status bar if it appears)
- Username `dmitry` in terminal prompt (crop terminal prompt line)
- Any `.env` files
- `_audit/` folder contents
- Paths like `/srv/pdf-extractor/` in terminal if avoidable

## Upload order for Upwork

1. Screenshot 2 (Architecture) — first impression, shows design skill
2. Screenshot 1 (Project Structure) — shows engineering discipline
3. Screenshot 3 (Results/Proof) — closes with evidence
