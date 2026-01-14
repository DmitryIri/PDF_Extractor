# ADR-005: Raw PDF Storage (FS vs Supabase Storage)

## Status
Proposed

## Context
Raw PDF (входной файл выпуска) является первичным артефактом пайплайна PDF Extractor.
Требования: детерминизм, воспроизводимость, audit trail, DR-ready, shared-server safety.

## Decision Drivers (Must-have)
1. Source of Truth: единый, однозначный, независимый от ephemeral FS.
2. Immutability: raw PDF после загрузки не перезаписывается (только новая версия как новый объект).
3. Audit trail: для каждого запуска фиксируется ссылка на raw (storage key) + checksum (sha256) + размер + время.
4. DR: восстановление сервера не должно зависеть от наличия raw на диске сервера.
5. Reproducibility: повторный прогон пайплайна по тому же raw должен быть возможен без ручных действий.
6. Least surprise on shared platform: минимизация “скрытых” папок с критичными файлами на сервере.

## Options Considered
A) FS-only (raw хранится только на Server_Latvia)
B) Supabase Storage-only (raw хранится только в Storage)
C) Hybrid: Supabase Storage = SoT, FS = processing cache (stage)

## Decision (Proposed)
Выбираем вариант C (Hybrid):
- Supabase Storage является Source of Truth для raw PDF (immutable object).
- На сервере используется рабочий кэш (stage) для обработки; его можно удалить и восстановить из Storage.

## Consequences
Positive:
- DR упрощается: raw вне сервера; server restore не блокирует доступ к raw.
- Явная трассировка: key + sha256 в таблице документов/запусков.
- FS перестаёт быть критичной точкой отказа.

Negative / Trade-offs:
- Нужна интеграция upload/download в n8n.
- Нужно определить bucket/prefix policy и ретеншн.

## Canonical Rules (Proposed)
1) Raw PDF key format:
   raw/<journal_code>/<YYYY>/<MM>/<issue_id>/<original_filename>

2) Immutability:
   - Запрещено перезаписывать объект по тому же key.
   - Любое “обновление” = новый key + новая запись метаданных.

3) Metadata must include:
   - storage_key
   - sha256
   - size_bytes
   - uploaded_at (UTC)
   - issue_id
   - original_filename

4) FS cache:
   - /srv/pdf-extractor/runtime/stage/<run_id>/
   - может очищаться автоматически, не является “истиной”.

