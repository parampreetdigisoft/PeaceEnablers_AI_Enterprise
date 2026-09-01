# Phase 5 — Enterprise Hardening

Not implemented in Phase 1. Folders and YAML knobs are shaped so this phase does not require a rewrite.

This folder will own:

- WORM / hash-chained audit logs, 7-year retention (PDF §7)
- Per-query cost tracking, budget alerts, semantic cache in Redis (PDF §2, §10)
- Circuit-breaker / degraded local-model mode (a Phase 1 skeleton already exists in `app/llm/router.py`)
- Deployment profiles: SaaS, VPC, sovereign, air-gapped, on-prem (PDF §5)
- Encryption, HSM keys, mTLS (PDF §6)
- Evaluation gates: Precision@5, hallucination classifier, ECE (PDF §3–4)
- Chaos drills and DR (PDF §13)

Do not put these concerns into `services/` or `jobs/` when they land — keep them here so Phase 1 code stays readable.
