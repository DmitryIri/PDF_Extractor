# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

PDF Extractor is a deterministic multi-agent pipeline for extracting individual articles from PDF issues of scientific journals. The project follows a production-first approach with DR architecture.

**Primary documentation:** `docs/design/pdf_extractor_techspec_v2.4.md` (canonical, self-contained)

## Architecture Invariants (Non-Negotiable)

1. **Python-only** — all computational logic in Python
2. **n8n is orchestrator only** — no business logic in n8n
3. **No LLM at runtime** — LLM only for design/documentation
4. **Determinism** — same input → same output
5. **Fail-fast** — errors via exit code + structured JSON; pipeline stops immediately
6. **T = L = E invariant** — article count in JSON = file names count = actual PDF files created
7. **Code ≠ Runtime** — code in `/opt/projects/pdf-extractor/`, runtime artifacts in `/srv/pdf-extractor/`

## Pipeline Components (Sequential Execution)

```
InputValidator → PDFInspector → MetadataExtractor → BoundaryDetector → Splitter → MetadataVerifier → OutputBuilder → OutputValidator
```

Each component:
- Reads JSON from stdin, writes JSON to stdout, logs to stderr
- Returns structured envelope: `{status, component, version, data, error}`
- Uses exit codes: 0=success, 10=invalid_input, 20=extraction_failed, 30=verification_failed, 40=build_failed, 50=internal_error

## Key Components

### MetadataExtractor (`agents/metadata_extractor/extractor.py`)
- Extracts raw anchors (DOI, text_block, ru_title, ru_authors, etc.) from PDF
- **Does NOT apply policy** — outputs observations only, no interpretation
- Uses PyMuPDF (fitz) for PDF parsing
- Policy for RU block extraction: `docs/policies/ru_blocks_extraction_policy_v_1_0.md`

### BoundaryDetector (`agents/boundary_detector/detector.py`)
- Core component that determines article boundaries from anchors
- **Single carrier of ArticleStartPolicy** — applies `policy_v1.py`
- DOI alone is NEVER sufficient for article start detection
- Requires all 5 RU blocks: ru_title, ru_authors, ru_affiliations, ru_address, ru_abstract
- Policy documentation: `docs/policies/article_start_detection_policy_v_1_0.md`

### InputValidator / PDFInspector
- Validation and structural inspection of input PDF
- Uses PyPDF2 and PyMuPDF respectively

## Running Components

Components are standalone Python scripts reading from stdin:

```bash
# Run InputValidator
echo '{"issue_id": "mg_2025_12", "journal_code": "mg", "pdf_path": "/path/to/file.pdf"}' | python agents/input_validator/validator.py

# Run MetadataExtractor
echo '{"issue_id": "mg_2025_12", "pdf": {"path": "/path/to/file.pdf"}}' | python agents/metadata_extractor/extractor.py

# Run BoundaryDetector (requires anchors JSON from MetadataExtractor)
cat anchors.json | python agents/boundary_detector/detector.py
```

## Dependencies

- Python 3.12+
- PyMuPDF (fitz) — PDF text/layout extraction
- PyPDF2 — PDF validation

Virtual environment: `.venv/`

## Policy Versioning

Policies are versioned and canonical. Changes require new version release (e.g., v1.0 → v1.1):
- `docs/policies/article_start_detection_policy_v_1_0.md`
- `agents/boundary_detector/policy_v1.py` — code implementation of policy

## File Layout

```
agents/           # Pipeline components (Python)
  input_validator/
  pdf_inspector/
  metadata_extractor/
  boundary_detector/
docs/             # Canonical documentation
  governance/     # Meta-documents (protocols, policies index)
  state/          # Project state (summaries, session logs)
  design/         # TechSpec, Plan, component designs
  policies/       # Versioned policy documents
tests/            # Unit and golden tests (empty, to be implemented)
scripts/          # Utility scripts (empty)
shared/           # Shared utilities (empty)
```

## Contract Schemas

Anchors (MetadataExtractor → BoundaryDetector):
```json
{"issue_id": "...", "total_pages": N, "anchors": [{page, type, value/text, bbox, confidence, ...}]}
```

Article starts (BoundaryDetector output):
```json
{"status": "success", "data": {"article_starts": [{start_page, confidence, signals: {...}}]}}
```
