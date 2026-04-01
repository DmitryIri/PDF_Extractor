# PDF Extractor

Deterministic multi-agent pipeline that splits scientific journal PDF issues into individually named article files — no LLM, no manual work, same input always produces the same output.

---

## Problem / Use Case

Scientific journals are often delivered as single monolithic PDF issues. This pipeline automatically detects article boundaries, extracts per-article metadata, splits into canonically named files, and verifies the result end-to-end — reproducibly, without human review.

---

## Pipeline

```
InputValidator → PDFInspector → MetadataExtractor → BoundaryDetector →
Splitter → MetadataVerifier → OutputBuilder → OutputValidator
```

8 isolated Python agents. Each reads JSON from stdin, writes JSON to stdout, and exits with a structured code. No shared state; strict contracts at every stage boundary.

---

## Output

For each processed journal issue:

```
export/
  articles/                    # Individual article PDFs with canonical filenames
  manifest/
    export_manifest.json       # Per-article metadata (pages, sha256, material_kind)
  checksums.sha256             # SHA-256 for every output file
  README.md                    # Human-readable delivery note
```

Filename pattern: `{JournalCode}_{YYYY}-{NN}_{PPP}-{PPP}_{AuthorSurname}.pdf`

---

## Quality Gates

**T = L = E invariant** — article count in manifest = filename count = actual PDFs on disk.
Validated by OutputValidator (exit 30 on any mismatch). SHA-256 verified end-to-end.

**Regression suite:** golden test fixture — 29 articles, 18 184 extracted anchors.
Validated on 6 production issues (29 + 8 + 9 + 6 + 11 + 9 articles) with T=L=E and SHA-256 verification end-to-end.

---

## Tech Stack

Python 3.12 · PyMuPDF · PyPDF2 · FastAPI · SQLite · asyncio · HTMX

---

## Requirements & Setup

- Python 3.12+
- Key dependencies: `pymupdf`, `pypdf2`, `fastapi`, `uvicorn`
- Create a virtual environment and install dependencies before running

Full environment setup and runtime configuration are documented in `docs/design/`.

---

## Example Invocation

```bash
tools/run_issue_pipeline.sh \
  --journal-code Mg \
  --issue-id mg_2025_12 \
  --pdf-path /path/to/Mg_2025-12.pdf \
  --run-id run_001
```

> **Note:** Requires a prepared environment and a real journal PDF.
> This shows the invocation pattern — not a zero-config quickstart.
> See `docs/design/` for full setup and configuration.

---

## Web UI

FastAPI + HTMX interface for issue upload, pipeline trigger, run monitoring, and one-click ZIP download of results.

---

## Security

This repository contains **no real journal PDFs and no credentials.**
Golden test fixtures contain extracted metadata (author names, titles) from published academic articles — publicly available information. Runtime artifacts live outside the repo.

---

## Documentation

- `docs/design/` — technical specification, architecture, boundary detection design
- `docs/policies/` — versioned extraction and naming policies
- `CLAUDE.md` — project instructions for Claude Code
