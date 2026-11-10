# RAG integration and demo data

## What runs

Set `ANALYZER=rag` to replace the amount-scanning placeholder. Existing upload,
analysis, review and invoice endpoints are unchanged. All suggestions remain pending;
the analyzer never approves a line or sends an invoice.

1. Split this project's extracted texts into overlapping chunks with exact source offsets.
2. Inventory work across **every** chunk in bounded batches, then consolidate synonymous names.
3. Embed chunks and work-item queries through Astropods (`titan-embed-text-v2`).
4. Rank each work item's evidence by vector similarity plus exact-term matches.
5. Ask `gpt-5-6-luna` for structured decisions based on retrieved evidence and dates.
6. Validate decimals, project currency, source quotes and client identity before returning items.
   The existing service verifies quotes again and stores items/evidence for review.

The model is prompted with a JSON schema; Pydantic validates its output. This gateway
path does not assume provider-enforced structured output support. Invalid JSON, refusal,
timeouts, incomplete embedding batches and provider errors fail the run. Previous items
remain available on failure.

Index scope is one analysis request / one project. Embeddings are rebuilt in memory;
there is no pgvector table or persistent cache in this version. Existing documents and
review results persist in the app database. Up to 150 chunks and 20 candidate items are
accepted; oversize inputs fail explicitly. Discovery/consolidation and retrieval can still
miss, duplicate or misinterpret work: this needs live-model evaluation, not just unit tests.
If retrieval cannot include all chunks, every affected item gets `low_confidence`.
Client approval/acceptance evidence needs a matching email author; contract-only billing
triggers conservatively remain flagged for human review. Email headers are imported
metadata, not cryptographic proof of the sender's identity.

## Astropods setup

The gateway is the service previously used in Bank Insights. It provides multiple models;
the `openai` Python package is only the compatible client, not an OpenAI subscription.
Set the following in the gitignored `backend/.env`:

```dotenv
ANALYZER=rag
ASTRO_GATEWAY_URL=https://YOUR_GATEWAY_HOST
ASTRO_GATEWAY_API_KEY=YOUR_GATEWAY_CREDENTIAL
RAG_MODEL=gpt-5-6-luna
RAG_EMBEDDING_MODEL=titan-embed-text-v2
```

Gateway URL can have `/v1` already; it is appended exactly once. Do not paste credentials
in issues, commits or frontend code. Only select `rag` when sending project text to the
configured gateway is intended. No fallback to invented demo answers occurs on errors.

Official references:
- https://docs.astropods.com/ai-gateway/chat
- https://docs.astropods.com/ai-gateway/models

## Docker

From the repo root, after creating `backend/.env`:

```sh
docker compose -f docker-compose.yml -f compose.rag.yml up --build -d
```

Backend: http://localhost:8000/docs. The existing frontend still runs separately.
The backend container uses the cloud gateway; the models themselves are not downloaded
into Docker. Database and upload volumes persist. The Compose overlay does not deploy
anything to the Astropods account. Configure credentials using the platform's current
project access; an older credential may no longer be authorized.

## Fictional demo archives

`demo/website.zip`: text contract plus 17 RFC822 `.eml` messages. Using a text contract
keeps regeneration dependency-free; the app's existing PDF importer also remains supported.
Project metadata and expected results are in `demo/expected.json`, **outside** the upload.
Use client `maya@northstar.example`, project `Northstar website`, currency EUR.

Expected review: EUR 600 website launch + EUR 200 authentication + revised EUR 80 analytics.
Dark theme EUR 150 must require approval/readiness review. Future mobile app EUR 5000 is
unrelated and must not be billed. Target after human review: EUR 880.

`demo/insufficient.zip`: no agreed price or completed work. Nothing should be clear to invoice.

From backend:

```sh
uv run python scripts/build_demo.py          # rebuild deterministic archives; no API calls
uv run python -m scripts.analyze_demo website # REAL gateway calls; consumes credits
uv run python -m scripts.analyze_demo insufficient
uv run pytest
uv run ruff check app/services/analysis scripts tests/test_rag.py tests/test_rag_integration.py
```

The live analysis command prints suggestions and the unflagged total. Compare individual
items, quotes, flags, omissions and duplicates with expected.json; totals alone are insufficient.
Never use expected.json as model input or as a substitute for model output.

## Verification scope (2026-11-10)

Local tests cover ingestion, retrieval, source/amount validation, author checks, review API
integration and preserving old items on provider failure. Docker health checks exercise
PostgreSQL and migrations. The Postman protocol fixture uses canned model responses: it
checks SDK request/response handling and failure behavior, not model accuracy.
The existing Bank Insights gateway credential returned HTTP 403 on a smoke request;
no successful live-model analysis or EUR 880 evaluation has been established yet.

Run the protocol fixture from repo root:

```sh
postman simulation run postman/simulations/rag.sim.yaml --port 4511 --no-history
# In another terminal, from backend:
uv run python -m scripts.check_gateway_simulation
```

PayPal integration is another team member's scope and is unchanged by this work.
