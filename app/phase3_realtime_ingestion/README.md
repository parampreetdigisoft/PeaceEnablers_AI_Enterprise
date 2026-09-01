# Phase 3 — Real-time Ingestion

Not implemented in Phase 1.

This folder will own:

- Document and news ingestion workers (GDELT, field reports, uploads)
- Pipeline capacity targets (≥ 1,000 documents/minute)
- Ingestion-to-alert latency ≤ 60 seconds
- PII detection / redaction before storage (enterprise PDF §8)
- Data classification labels on every ingested object (PDF §11)
- Hot → warm → cold → archive lifecycle

Until then, Phase 1 document ingest lives in `app/services/document_service.py` (on-demand, coalesced by document id).
