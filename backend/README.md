# AI IELTS Tutor — Backend

Async **FastAPI** service for the AI IELTS Tutor platform. Layered as
`routes → controllers → models`, provider-agnostic AI, SQLAlchemy (async) with
Alembic migrations, JWT auth + RBAC, rate limiting, and an RFC 7807 error
contract. Runs on **SQLite out of the box** (zero config) and on **PostgreSQL**
(Supabase) in production.

## Requirements

- Python **3.12**
- (Optional) Docker + Docker Compose for the containerized stack

## Quickstart (local, SQLite)

```bash
cd backend
python -m venv .venv
source .venv/Scripts/activate        # Windows Git Bash;  Linux/mac: source .venv/bin/activate
pip install -r requirements.txt
uvicorn main:app --reload --port 8000
```

- API root: <http://localhost:8000/>
- Interactive docs (OpenAPI): <http://localhost:8000/docs>
- Health / readiness: <http://localhost:8000/health>, <http://localhost:8000/ready>

On SQLite the tables are auto-created on startup and a **demo admin** is seeded:

| Field | Value |
|-------|-------|
| Email | `admin@ielts.local` |
| Password | `AdminPass123` |

> The AI layer uses an **offline mock provider** unless `GROQ_API_KEY` is set, so
> scoring works with no external calls.

## Docker (API + PostgreSQL)

```bash
# from the repository root
docker compose up --build
```

This starts PostgreSQL 16 and the API (which runs `alembic upgrade head` before
serving). API on <http://localhost:8000>.

Build just the image:

```bash
docker build -t ai-ielts-backend ./backend
```

## Database & migrations

- **Dev (SQLite):** tables auto-created on startup — no migration step needed.
- **Production (PostgreSQL):** schema is managed by Alembic.

```bash
alembic upgrade head          # apply all migrations
alembic downgrade base        # roll everything back
alembic history               # list revisions
```

Set the target DB via `DATABASE_URL`, e.g.
`postgresql+asyncpg://user:pass@host:5432/dbname`.

## Environment variables

Copy `.env.example` → `.env`. Key settings:

| Variable | Default | Purpose |
|----------|---------|---------|
| `DATABASE_URL` | `sqlite+aiosqlite:///./dev.db` | DB connection (async driver) |
| `JWT_SECRET` | dev placeholder | **Set in production** |
| `ACCESS_TOKEN_TTL_MIN` | `15` | Access-token lifetime |
| `REFRESH_TOKEN_TTL_DAYS` | `30` | Refresh-token lifetime |
| `AI_PROVIDER` | `groq` | AI provider (falls back to mock without a key) |
| `GROQ_API_KEY` | empty | Enables real Groq inference |
| `RATE_LIMIT_ENABLED` | `true` | Toggle rate limiting |
| `RATE_LIMIT_LOGIN_PER_MIN` | `10` | Login attempts / min / IP |
| `RATE_LIMIT_REGISTER_PER_MIN` | `5` | Registrations / min / IP |
| `RATE_LIMIT_AI_PER_MIN` | `20` | AI scoring calls / min / user |
| `SEED_ADMIN_EMAIL` / `SEED_ADMIN_PASSWORD` | see above | Dev admin (SQLite) |

## Testing

Isolated integration smoke suites (FastAPI `TestClient` + SQLite), run in
separate processes:

```bash
python tests/run_smoke.py
```

CI (GitHub Actions) runs, on every push/PR: `compileall` → Alembic
`upgrade head` + `downgrade base` → all smoke suites → Docker image build +
`/health` check.

## API map

Everything except the probes is under the `/v1` prefix.

**Root:** `GET /` · `GET /health` · `GET /ready`

**Auth** `/v1/auth`: `POST /register` · `POST /login` · `POST /refresh` ·
`POST /logout` · `GET /me`

**Onboarding / Profile:** `POST /v1/onboarding` · `GET|PATCH /v1/profile`

**Learner self-service** `/v1/me`: `GET /weaknesses` · `GET /adaptive-difficulty`
· `GET /recommendations`

**Writing:** `POST /v1/writing/attempts` · `GET /v1/writing/attempts/{id}` ·
`GET /v1/writing/history`

**Reading:** `GET /v1/reading/passages` · `POST /v1/reading/attempts` ·
`GET /v1/reading/attempts/{id}` · `GET /v1/reading/history`

**Listening:** `GET /v1/listening/clips` · `POST /v1/listening/attempts` ·
`GET /v1/listening/attempts/{id}` · `GET /v1/listening/history`

**Speaking:** `POST /v1/speaking/attempts` · `GET /v1/speaking/attempts/{id}` ·
`GET /v1/speaking/history`

**Analytics:** `GET /v1/analytics/progress` · `GET /v1/analytics/prediction` ·
`GET /v1/analytics/overview`

**Admin** `/v1/admin` (RBAC): `GET /ai-usage` · `GET /users` · `PATCH /users/{id}`
· passages/questions CRUD (`/passages`, `/passages/{id}`,
`/passages/{id}/questions`, `/questions/{id}`)

## Project structure

```
backend/
├── main.py               # app factory, middleware, lifespan, router mounting
├── core/                 # config, security, validation, rate_limit, predictor, band_mapping
├── db/                   # async engine/session, declarative base + mixins
├── models/               # SQLAlchemy ORM models
├── controllers/          # business logic + Pydantic schemas (camelCase I/O)
├── routes/               # thin HTTP layer (one module per domain)
├── middleware/           # correlation-id + RFC 7807 error handlers
├── ai/                   # LLMProvider port, providers (groq/mock), orchestrator, rubrics
├── alembic/              # migrations
└── tests/                # smoke suites + run_smoke.py runner
```
