# Raw Ingest Contract (n8n) — Canonical

## Status
Canonical

## Purpose
This contract defines the only допустимый вход raw PDF в пайплайн PDF Extractor.
Контракт обязателен для n8n Webhook и для будущего UI (UI = клиент этого же контракта).

Ключевые свойства: детерминизм, воспроизводимость, audit trail, DR-ready.

---

## Entry Point
Transport: HTTP Webhook (n8n)  
Content-Type: multipart/form-data

---

## Required Input Fields (MUST)
The request MUST include all fields below:

1) file (binary)
- Raw PDF file of the issue.
- MUST be a valid PDF.
- MUST be non-empty.

2) journal_code (string)
- Examples: Mg, Na, PMH
- MUST be non-empty.
- Allowed charset: [A-Za-z0-9_-]

3) issue_id (string)
- Example: Mg_2025-05
- MUST be non-empty.
- Allowed charset: [A-Za-z0-9_-]

4) year (integer)
- MUST be 4-digit year.
- Range check MUST be applied.

5) month (integer)
- MUST be 1..12.

If ANY required field is missing or invalid → HARD STOP (pipeline must not start).

---

## Forbidden Input Fields (MUST NOT)
The client MUST NOT send:
- storage_key
- sha256
- size_bytes
- ingest_run_id

These fields are system-calculated only.

---

## System-Calculated Fields (CALCULATED)
The system MUST calculate and persist:

- original_filename (from upload)
- size_bytes (from upload)
- sha256 (computed on file bytes)
- storage_key (canonical, see below)
- uploaded_at_utc (UTC)
- ingest_run_id (unique ID for ingestion/run)
- journal_code, issue_id, year, month (as received, validated)

Filesystem paths are explicitly NOT metadata.

---

## Canonical Storage Target
Supabase Storage:
- Bucket: pdf-raw
- Object key (storage_key):

raw/<journal_code>/<year>/<month>/<issue_id>/<original_filename>

Example:
raw/Mg/2025/05/Mg_2025-05/Mg_2025-05.pdf

---

## Immutability Rules (HARD)
- Overwrite of an existing object at the same storage_key is strictly forbidden.
- Any corrected/updated PDF MUST be uploaded under a NEW storage_key.
- Same filename does not imply same content; sha256 is authoritative.

---

## Ingest Gate: Success Criteria (ALL MUST PASS)
The pipeline may proceed to processing ONLY if all are true:

1) raw PDF successfully uploaded to Supabase Storage (bucket pdf-raw)
2) sha256 computed successfully
3) size_bytes captured successfully
4) metadata persisted successfully (DB)
5) ingest_run_id created and linked to metadata
6) all steps above completed successfully with explicit success acknowledgement

If any step fails → HARD STOP (no processing stage must start).

---

## Failure Handling (HARD STOP)
If ingest fails, the pipeline MUST:
- stop execution,
- return an explicit error,
- NOT start FS stage,
- NOT produce outputs.

No “partial success” is allowed.

---

## Reproducibility & DR Invariant
Any run MUST be reproducible using:
- storage_key
- sha256
- ingest_run_id

Loss of Server_Latvia must not cause loss of raw PDF:
raw must remain recoverable from Supabase Storage independently of server filesystem.

