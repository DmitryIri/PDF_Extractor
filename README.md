# PDF Extractor

**Deterministic multi-agent pipeline** for extracting individual articles from PDF issues of scientific journals.

---

## Pipeline at a glance

```
InputValidator → PDFInspector → MetadataExtractor → BoundaryDetector
                                                          ↓
                OutputValidator ← OutputBuilder ← MetadataVerifier ← Splitter
```

8 isolated Python agents. Each reads JSON from stdin, writes JSON to stdout, exits with a structured code. No LLM at runtime — fully deterministic, same input always produces the same output.

---

## Outputs

For each processed journal issue the pipeline produces:

```
export/
  articles/            # Individual article PDFs with canonical filenames
  manifest/
    export_manifest.json   # Per-article metadata (pages, sha256, material_kind)
  checksums.sha256     # SHA-256 for every output file
  README.md            # Human-readable delivery note
```

Filename pattern: `{JournalCode}_{YYYY}-{NN}_{PPP}-{PPP}_{AuthorSurname}.pdf`

---

## Quality gates / Validation

**T = L = E invariant** — article count in manifest = filename count = actual PDF files on disk.
Validated by OutputValidator (exit 30 on any mismatch). SHA-256 verified end-to-end.

**Regression suite:** golden test fixture with 29 articles, 18 184 extracted anchors. Validated on 4 production issues with T=L=E and SHA-256 verification end-to-end.

---

## Web UI (Phase 3)

FastAPI + HTMX web interface for issue upload, pipeline trigger, run status, and one-click ZIP download of results.

---

## Security note

This repository contains **no real journal PDFs and no credentials.**
Golden test fixtures contain extracted metadata (author names, titles) from published academic articles — publicly available information. Runtime artifacts (actual PDFs, exports) live outside the repo in `/srv/`.

---

## Canonical documentation

- `docs/design/pdf_extractor_techspec_v_2_8.md` — full technical specification
- `docs/policies/` — versioned extraction and naming policies
- `GATE0_PROOF.md` — deterministic detection proof (pre-implementation)
