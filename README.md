# ScopeProof

ScopeProof turns agreed work into accurate invoices. It reads contracts, client conversations and
work logs, extracts what was actually agreed (prices, milestones, approved extras) and drafts
invoice line items that link back to their sources. When something is unclear or contradictory,
it flags the item for review instead of making up a price.

> **Status:** the full flow works end to end: projects → ZIP/.eml upload → analysis → review → invoice →
> send → payment tracking. Payments default to a **placeholder engine**. RAG is available through Astropods
> behind the existing interface; gateway access and live-model quality still need qualification (see
> [Integration points](#integration-points-rag--paypal)).

## Stack

| Layer    | Tech                                                              |
| -------- | ----------------------------------------------------------------- |
| Frontend | Next.js 16 (App Router), React 19, TypeScript, Tailwind CSS v4    |
| Backend  | FastAPI, SQLAlchemy 2.0 (async), Alembic, Pydantic v2, uv         |
| Database | PostgreSQL 16 (via Docker Compose)                                |
| Auth     | Email + password, Argon2 hashing, JWT bearer tokens               |

**Why SQLAlchemy and not Prisma?** The Python Prisma client is no longer maintained. SQLAlchemy and
Alembic are the standard choice with FastAPI: async support, typed models and versioned migrations.
SQLAlchemy also works with `pgvector`, which we'll need for RAG embeddings in Postgres.

## Getting started

Prerequisites: Docker, Node 20+, Python 3.12+, [uv](https://docs.astral.sh/uv/).

```bash
# 1. Database (Postgres on localhost:5433)
docker compose up -d

# 2. Backend: http://localhost:8000 (interactive docs at /docs)
cd backend
cp .env.example .env          # then set JWT_SECRET_KEY
uv sync
uv run alembic upgrade head
uv run fastapi dev app/main.py

# 3. Frontend: http://localhost:3000
cd frontend
cp .env.example .env.local
npm install
npm run dev
```

## Project structure

```
ScopeProof/
├── docker-compose.yml          # Postgres
├── backend/
│   ├── app/
│   │   ├── main.py             # FastAPI app, CORS, router mount
│   │   ├── core/               # settings (env), security (hashing, JWT)
│   │   ├── db/                 # declarative Base + mixins, async session
│   │   ├── models/             # SQLAlchemy models (register new ones in __init__.py)
│   │   ├── schemas/            # Pydantic request/response models
│   │   ├── services/           # business logic (no HTTP concerns)
│   │   └── api/
│   │       ├── deps.py         # DB session + current-user dependencies
│   │       └── v1/
│   │           ├── router.py   # mounts all endpoint routers
│   │           └── endpoints/  # auth, users, health
│   ├── alembic/                # migrations
│   └── tests/                  # pytest (in-memory SQLite, no Postgres needed)
└── frontend/
    └── src/
        ├── app/
        │   ├── (marketing)/    # landing page
        │   ├── (auth)/         # login, register
        │   └── (app)/          # authenticated area (dashboard), guarded
        ├── components/
        │   ├── ui/             # Button, Input, Logo primitives
        │   ├── landing/        # landing page sections
        │   └── auth/           # forms, route guard
        ├── lib/                # API client, token storage, config
        ├── providers/          # AuthProvider (session state)
        └── types/
```

## API

All project routes need a Bearer token and only return the caller's own projects.

| Method | Path                                          | Description                                          |
| ------ | --------------------------------------------- | ---------------------------------------------------- |
| GET    | `/api/v1/health`                              | API + database health                                |
| POST   | `/api/v1/auth/register`                       | Create account (JSON)                                |
| POST   | `/api/v1/auth/login`                          | OAuth2 password form (`username`=email) → JWT        |
| GET    | `/api/v1/users/me`                            | Current user                                         |
| GET    | `/api/v1/projects`                            | List projects with progress stats                    |
| POST   | `/api/v1/projects`                            | Create project + client details                      |
| GET    | `/api/v1/projects/{id}`                       | Project + stats                                      |
| PATCH  | `/api/v1/projects/{id}`                       | Update project / client details                      |
| DELETE | `/api/v1/projects/{id}`                       | Delete project, files, items and invoices            |
| GET    | `/api/v1/projects/{id}/documents`             | List documents (contract first, emails by date)      |
| POST   | `/api/v1/projects/{id}/documents`             | Multipart `files`: ZIP and/or .eml/.pdf/.txt/.md     |
| GET    | `/api/v1/projects/{id}/documents/{doc}`       | Extracted text + metadata (author, recipients, date) |
| GET    | `/api/v1/projects/{id}/documents/{doc}/file`  | Original file                                        |
| PATCH  | `/api/v1/projects/{id}/documents/{doc}`       | Change kind (contract / email / note)                |
| DELETE | `/api/v1/projects/{id}/documents/{doc}`       | Delete document                                      |
| POST   | `/api/v1/projects/{id}/analysis`              | Run the analyzer; replaces earlier suggestions       |
| GET    | `/api/v1/projects/{id}/review`                | Items + evidence + totals + lock state               |
| POST   | `/api/v1/projects/{id}/items`                 | Add an item by hand                                  |
| PATCH  | `/api/v1/projects/{id}/items/{item}`          | Edit / approve / exclude (`acknowledge_flags` for flagged) |
| DELETE | `/api/v1/projects/{id}/items/{item}`          | Delete a manual item                                 |
| POST   | `/api/v1/projects/{id}/items/approve-clear`   | Approve all unflagged items that have a price        |
| GET    | `/api/v1/projects/{id}/invoice`               | Active invoice + earlier (cancelled) ones            |
| POST   | `/api/v1/projects/{id}/invoice`               | Confirm draft from approved items (locks items)      |
| POST   | `/api/v1/projects/{id}/invoice/reopen`        | Discard a confirmed, unsent invoice                  |
| POST   | `/api/v1/projects/{id}/invoice/send`          | Send through the payment provider                    |
| POST   | `/api/v1/projects/{id}/invoice/refresh`       | Pull payment status from the provider                |
| POST   | `/api/v1/projects/{id}/invoice/cancel`        | Cancel a sent, unpaid invoice                        |

### Review rules

- Every item must be approved or excluded before the invoice can be confirmed.
- Approving needs a price. Approving an item with open flags needs `acknowledge_flags: true` (the UI
  asks the user to confirm).
- Every evidence quote is checked against the stored document text; quotes that can't be found are
  marked unverified, and an item with no verified quote gets the `unsupported` flag.
- While an invoice is confirmed/sent/paid, items and analysis are locked (409).

## Integration points (RAG + PayPal)

Both engines are selected in `backend/.env` and only need to implement one small interface.

**RAG analyzer**: `ANALYZER=rag`

Implemented in this branch using Astropods AI Gateway. See [setup, demo and verification](docs/RAG.md). Live access still needs a valid gateway credential.

- Interface and data types: `backend/app/services/analysis/base.py` (`Analyzer`, `SourceDocument`,
  `ItemSuggestion`, `EvidenceSuggestion`, `Flag`, flag codes, evidence roles).
- Input: the project's processed documents with text, author, recipients and date.
- Output: suggested items with evidence quotes copied verbatim from the documents, plus flags
  (`missing_approval`, `conflicting_price`, `unclear_price`, `not_ready`, `low_confidence`).
- Register it in `backend/app/services/analysis/__init__.py`. Storage, quote verification and
  the whole review UI already work with whatever it returns. `placeholder.py` (a simple amount
  scan) is the current stand-in.

**PayPal sandbox**: `PAYMENT_PROVIDER=paypal`

- Interface: `backend/app/services/payments/base.py` (`PaymentProvider`: `send_invoice`,
  `get_status`, `cancel_invoice`, returning `ProviderInvoice`).
- Statuses use PayPal's names (`SENT`, `PAID`, `CANCELLED`, …); `PROVIDER_STATUS_MAP` maps them to
  the app's invoice statuses.
- Register it in `backend/app/services/payments/__init__.py`. For webhooks, look up the invoice by
  `provider_invoice_id` and call `invoice_service.apply_provider_status(...)`.

## Common tasks

```bash
# Backend
uv run pytest                                          # tests
uv run ruff check . && uv run ruff format .            # lint + format
uv run alembic revision --autogenerate -m "message"    # new migration after model changes

# Frontend
npm run lint
npm run build
```

## Adding a feature module (backend)

1. Model in `app/models/<name>.py` and import it in `app/models/__init__.py`
2. Schemas in `app/schemas/<name>.py`
3. Logic in `app/services/<name>_service.py`
4. Router in `app/api/v1/endpoints/<name>.py`, included in `app/api/v1/router.py`
5. `uv run alembic revision --autogenerate -m "add <name>"`

## Roadmap

- [x] Landing page, auth, project skeleton
- [x] Projects: one contract + its paper trail, client details
- [x] Document upload and ingestion (ZIP, .eml with authors/dates/threading, PDF, text)
- [x] Review queue: evidence quotes, flags, edit / approve / exclude, manual items
- [x] Invoice draft → confirm → send → payment tracking (placeholder provider)
- [x] RAG analyzer: project-local chunking, gateway embeddings, retrieval and validated citations
- [ ] Qualify live-model results against demo fixtures; persistent pgvector indexing
- [ ] PayPal sandbox provider + payment webhooks
- [ ] Gmail sync instead of ZIP upload

## Known starter shortcuts

- Uploaded files are stored on local disk (`backend/storage/`, gitignored). Move to object storage
  before deploying.
- Analysis runs inside the request. That's fine for the placeholder; a slow RAG run may want a
  background job with the existing `AnalysisRun.status` field.
- The access token is stored in `localStorage` and the dashboard is protected client-side.
  Before production, move to httpOnly cookies (+ refresh tokens) and a server-side check.
