# PEM Aevum AI Service (Phase 1)

FastAPI AI layer for the Peace Enablers / PEM Aevum platform. This service **does not own authentication**. The ASP.NET Core API is the identity source of truth; it calls this service internally and must send:

| Header | Purpose |
|---|---|
| `X-API-Key` | Shared service secret (same as the current AI service) |
| `X-User-Id` | Calling user, logged on every request and every job |
| `X-User-Roles` | Comma-separated: `Admin`, `Analyst`, `Viewer` |
| `X-User-Email` | Optional |

If `X-User-Roles` is omitted, the service treats the caller as `Analyst` so existing .NET clients keep working (`app/config/rbac.yaml`).

## Run

```powershell
cd D:\Ranjeet\projects\Peace-enablers\code\PeaceEnablers_AI_Enterprise
.\.venv\Scripts\Activate.ps1
python run.py
```

Docs: `http://127.0.0.1:8000/docs`  
Health: `http://127.0.0.1:8000/health`

SQL Server, OpenAI, and the API key come from `.env` (see `.env.example`). Nothing in source is hardcoded.

## Endpoint compatibility

Paths match `PeaceEnablers_AI_Service` so the .NET client does not need a rewrite:

- `POST /api/chat/ask|country|global|cross-comparision|executive-slides|kpi-summary`
- `GET  /api/chat/emerging-trends-and-issues|pillar-live-signals`
- `POST /api/countries-score-analysis/analyze/...`
- `POST /api/rag/process-document/{id}` and `delete-document/{id}`

New Phase 1 surfaces:

- `GET  /api/jobs/{jobId}` — caller job status
- `GET  /api/admin/health` — SQL + vector + graph + LLM
- `GET  /api/admin/jobs` — queued/running jobs with country, pillar, question, attached users, elapsed time, provider
- `GET  /api/admin/countries/{id}/status` — pillar/question progress
- `POST /api/admin/jobs/{jobId}/cancel` — Admin only

Evaluation endpoints still return immediately. The body now also includes `jobId` and `coalesced` (true when this caller attached to an in-flight job).

## How a request flows

1. `middleware/user_context.py` attaches the calling user.
2. `middleware/request_logging.py` writes an append-only line to `logs/requests.log`.
3. Route → `services/*` (the only place that knows the use-case flow).
4. Service asks `jobs/manager.py` for a job on the YAML coalescing key.
5. Duplicate concurrent request → attached; **no second LLM call**.
6. New job → `llm/router.py` picks a provider from `config/llm_routing.yaml` and runs **once**.
7. Result saved via `repositories/*` (the only layer that touches SQL).

Chat answers use `retrieval/`: **SQL first**, then vector DB, then web fallback (stub in Phase 1).

## Tune without code

| File | What it controls |
|---|---|
| `app/config/job_coalescing.yaml` | What counts as “the same resource” (`country` /        `country_pillar` / `country_pillar_question`) |
| `app/config/llm_routing.yaml` | Active providers, tiers, fallback, circuit breaker |
| `app/config/logging.yaml` | Log paths and fields |
| `app/config/rbac.yaml` | Header names and role policies |

If only one LLM provider is `enabled: true`, the router never fans out. Job coalescing is what guarantees one execution per resource even with many users.

## Folder responsibilities (no overlap)

| Folder | Single responsibility |
|---|---|
| `api/routes/` | HTTP only — path, status, schema |
| `core/` | Settings loader, security, logging setup, exceptions |
| `config/` | Operator-edited YAML (not Python) |
| `middleware/` | Cross-cutting: user attribution + request file logging |
| `models/` | Domain entities (job, evaluation node, audit) |
| `schemas/` | Pydantic wire contracts |
| `jobs/` | Coalescing engine (key, registry, manager) |
| `llm/` | Providers, router, cache, prompts |
| `retrieval/` | SQL → vector → web fallback order |
| `services/` | Use-case orchestration |
| `repositories/` | SQL / persistence only |
| `database/` | Connection factories: SQL Server, Chroma, Neo4j stub |
| `phase2_*` … `phase5_*` | Stubs only — see each README |

## Tests

```powershell
python -m pytest tests -q
```
