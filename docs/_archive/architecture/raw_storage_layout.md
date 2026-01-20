# Raw PDF Storage — Canonical Layout

## Scope
This document defines the canonical storage layout and invariants for raw PDF files
used by the PDF Extractor pipeline.

Raw PDF is a critical input artifact and must follow strict rules regarding
immutability, auditability, and disaster recovery.

---

## Source of Truth
Supabase Storage is the single Source of Truth for all raw PDF files.

Local filesystem storage on Server_Latvia is permitted only as a temporary
processing stage and must never be treated as authoritative.

---

## Storage Bucket
pdf-raw

This bucket is reserved exclusively for raw (input) PDF files.

---

## Object Key Structure
raw/<journal_code>/<year>/<month>/<issue_id>/<original_filename>

### Example
raw/Mg/2025/05/Mg_2025-05/Mg_2025-05.pdf

---

## Immutability Rule
Each object stored under a given storage key is immutable.

- Overwriting an existing object is strictly prohibited.
- Any updated or corrected PDF must be uploaded under a new storage key.
- Identical filenames do not imply identity of content.

---

## Mandatory Metadata (Logical Model)
The following metadata MUST exist for each raw PDF:

- storage_key
- original_filename
- sha256
- size_bytes
- uploaded_at_utc
- journal_code
- issue_id
- ingest_run_id

Filesystem paths are explicitly NOT considered metadata.

---

## Pipeline Entry Point
Raw PDF enters the pipeline exclusively via:

UI / Webhook Upload
→ Supabase Storage (pdf-raw)
→ Metadata persistence
→ Pipeline execution

The pipeline must not start unless raw PDF upload and metadata persistence
have been completed successfully.

---

## Filesystem Processing Stage
During processing, raw PDF may be temporarily materialized under:

/srv/pdf-extractor/runtime/stage/<run_id>/

This directory:
- is ephemeral
- may be deleted at any time
- must be fully reconstructible from Supabase Storage

---

## Disaster Recovery Invariant
Loss of Server_Latvia must not result in loss of raw PDF data.

Raw PDFs must always be recoverable from Supabase Storage without reliance
on local filesystem artifacts.

---

## Status
Canonical
