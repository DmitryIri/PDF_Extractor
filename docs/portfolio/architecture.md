# PDF Extractor — Architecture Overview

```
                        INPUT
                          │
                    PDF + issue_id
                          │
                          ▼
               ┌─────────────────────┐
               │   InputValidator    │  validates PDF exists, readable, named correctly
               └──────────┬──────────┘
                          │
                          ▼
               ┌─────────────────────┐
               │    PDFInspector     │  total pages, is_encrypted, file_size
               └──────────┬──────────┘
                          │
                          ▼
               ┌─────────────────────┐
               │  MetadataExtractor  │  extracts anchors: DOI, ru_title, ru_authors,
               │                     │  ru_affiliations, ru_abstract, contents_marker,
               │                     │  text_blocks  → 18 000+ anchors per issue
               └──────────┬──────────┘
                          │  anchors.json
                          ▼
               ┌─────────────────────┐
               │  BoundaryDetector   │  applies ArticleStartPolicy v1.0
               │                     │  → article_starts with confidence + material_kind
               │                     │  → boundary ranges [from_page, to_page]
               └──────────┬──────────┘
                          │  boundaries.json
                          ▼
               ┌─────────────────────┐
               │      Splitter       │  physical PDF split by page ranges (PyMuPDF)
               │                     │  SHA-256 stable across runs
               └──────────┬──────────┘
                          │  split PDFs + manifest
                          ▼
               ┌─────────────────────┐
               │  MetadataVerifier   │  surname extraction (STEP A→B→C algorithm)
               │                     │  GOST 7.79-2000 transliteration
               │                     │  TOC re-verification
               │                     │  → expected_filename per article
               └──────────┬──────────┘
                          │  verified manifest
                          ▼
               ┌─────────────────────┐
               │    OutputBuilder    │  assembles export directory (atomic write)
               │                     │  articles/ + manifest/ + checksums.sha256
               └──────────┬──────────┘
                          │  export path
                          ▼
               ┌─────────────────────┐
               │   OutputValidator   │  T=L=E invariant check
               │                     │  SHA-256 verification
               │                     │  filename pattern validation
               └──────────┬──────────┘
                          │
                        OUTPUT
                          │
              export/articles/*.pdf  (canonical filenames)
              export/manifest/export_manifest.json
              export/checksums.sha256
```

## Key design decisions

| Decision | Rationale |
|---|---|
| Python-only, no LLM at runtime | Determinism — same input → same output |
| JSON stdin/stdout contracts | Each agent independently testable |
| Exit codes (0/10/20/30/40/50) | Fail-fast — pipeline stops on first error |
| T=L=E invariant | Hard guarantee on completeness |
| Code ≠ Runtime paths | DR safety — `/opt/projects/` vs `/srv/` |
| Atomic write (.tmp → rename) | No partial exports on failure |

## Material kinds

| Kind | Filename suffix | Detection rule |
|---|---|---|
| `research` | `_{AuthorSurname}.pdf` | ru_title + ru_authors + ru_affiliations + ru_address + ru_abstract |
| `contents` | `_Contents.pdf` | contents_marker anchor |
| `editorial` | `_Editorial.pdf` | article start without extractable authors |
| `info` | `_Info.pdf` | standalone "ИНФОРМАЦИЯ" block, no DOI |

## Production validation

| Issue | Articles | T=L=E | SHA-256 |
|---|---|---|---|
| mg_2025_12 (golden test) | 29 | ✅ | verified |
| mg_2026_01 | 8 | ✅ | verified |
| mh_2026_02 | 9 | ✅ | verified |
| na_2026_02 | 6 | ✅ | verified |
