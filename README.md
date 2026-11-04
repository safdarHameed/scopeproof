# ScopeProof

ScopeProof turns agreed work into accurate invoices. It reads contracts, client conversations and
work logs, extracts what was actually agreed (prices, milestones, approved extras) and drafts
invoice line items that link back to their sources. When something is unclear or contradictory,
it flags the item for review instead of making up a price.

> **Status:** starter repo. It includes the landing page, authentication and the project structure.
> Core features (document ingestion, RAG, invoice drafting, PayPal) are not built yet.

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

| Method | Path                    | Description                                        |
| ------ | ----------------------- | -------------------------------------------------- |
| GET    | `/api/v1/health`        | API + database health                              |
| POST   | `/api/v1/auth/register` | Create account (JSON)                              |
| POST   | `/api/v1/auth/login`    | OAuth2 password form (`username`=email) → JWT      |
| GET    | `/api/v1/users/me`      | Current user (Bearer token)                        |

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
- [ ] Projects: one contract + its paper trail
- [ ] Document upload and ingestion (PDF, email/chat exports, work logs)
- [ ] Chunking + embeddings in Postgres (`pgvector`)
- [ ] Extraction of agreed terms with source citations
- [ ] Conflict / missing-approval detection → review queue
- [ ] Editable invoice draft with evidence links
- [ ] PayPal sandbox invoicing + payment webhooks

## Known starter shortcuts

- The access token is stored in `localStorage` and the dashboard is protected client-side.
  Before production, move to httpOnly cookies (+ refresh tokens) and a server-side check.
