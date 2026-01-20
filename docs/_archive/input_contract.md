# PDF Extractor — Input Contract (MVP)

## Назначение

Input Contract определяет единственный допустимый формат входных данных
для всех агентов пайплайна PDF Extractor.

Любой агент:
- читает ТОЛЬКО объект `input`
- НЕ читает `binary.*`
- НЕ зависит от n8n-специфичных структур

## Source of Truth

Единственный источник истины — объект `input`.

Любые данные вне `input`:
- считаются runtime-контекстом
- не используются для принятия решений агентами

## Контракт (канонический JSON)

```json
{
  "input": {
    "file_name": "Mg_2025-12.pdf",
    "mime_type": "application/pdf",
    "file_size": 8755610,
    "received_at": "2025-12-25T14:28:34.789+02:00",
    "source": "n8n_webhook",
    "pipeline": "pdf-extractor",
    "stage": "ingress_normalized"
  }
}
```

## Архитектурные правила

1. Ни один агент не читает `binary.*`
2. Контракт immutable в рамках одного run
3. Любое расширение контракта фиксируется документально
4. Runtime-поля не входят в `input`

## Статус

Версия: MVP v1
Статус: Canonical
