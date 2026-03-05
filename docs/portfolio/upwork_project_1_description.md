# Upwork Portfolio — Project Description

## Project title (for Upwork "Project Title" field)
PDF Article Extractor — Deterministic Multi-Agent Pipeline

## Project description (paste into "Add content" / description field)

```
Built a production-ready Python pipeline that automatically splits scientific journal PDF issues into individual article files.

The system uses 8 isolated agents connected by strict JSON contracts:

InputValidator → PDFInspector → MetadataExtractor → BoundaryDetector → Splitter → MetadataVerifier → OutputBuilder → OutputValidator

Each agent is independently testable and deterministic — same PDF always produces the same output files.

Key technical highlights:
• No LLM at runtime — pure deterministic rule-based detection
• T=L=E invariant: article count in manifest = filenames = actual PDFs on disk (hard guarantee)
• SHA-256 end-to-end verification
• 18,000+ text anchors extracted per issue for boundary detection
• GOST 7.79-2000 transliteration for canonical filenames
• FastAPI + HTMX web UI for upload, processing, and ZIP download
• Validated on 4 production issues (29 + 8 + 9 + 6 articles) with T=L=E and SHA-256 verification

Stack: Python 3.12, PyMuPDF, FastAPI, SQLite, asyncio
```

## Skills tags (Upwork "Skills" field, pick relevant)
- Python
- PDF Processing
- API Development
- FastAPI
- Software Architecture
- Algorithm Design
- Automation

## Role (for "Your role" field)
Solo developer — architecture, implementation, testing, deployment

## Notes for yourself
- Repository: github.com/DmitryIri/PDF_Extractor (currently private — make public or fork as portfolio-public)
- Upload screenshots in order: Architecture → Project Structure → Results proof
- If asked about the "journal names": say "scientific journals in Russian medical domain" — no need to name specific titles
- If asked about scale: "4 production issues processed end-to-end, each 6-29 articles"
