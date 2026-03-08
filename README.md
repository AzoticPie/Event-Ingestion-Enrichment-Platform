# Event Ingestion & Enrichment Platform

Backend service for tenant-scoped event ingestion, asynchronous enrichment, and query/aggregate APIs.

## Milestone 1 scope

- Project skeleton and dependency management
- Configuration and structured logging
- Health and readiness endpoints
- Architecture docs, API spec draft, ADRs
- Docker Compose setup for API, worker, Postgres, and Redis

## Tech stack

- Python 3.12+
- FastAPI
- PostgreSQL
- Redis
- SQLAlchemy 2.0 (wired in next milestone)
- Celery

## Quickstart

1. Copy environment variables:

   ```bash
   cp .env.example .env
   ```

2. Build and start services:

   ```bash
   docker compose up --build
   ```

3. Open services:

   - Frontend: `http://localhost:5173`
   - API docs: `http://localhost:8000/docs`

4. Validate health endpoints:

   - `GET http://localhost:8000/health/live`
   - `GET http://localhost:8000/health/ready`

## Containerized frontend notes

- The frontend is built from [`frontend/Dockerfile`](frontend/Dockerfile) and served by Nginx.
- Frontend runtime in Compose is exposed at `http://localhost:5173`.
- API base URL injected at frontend build time uses `FRONTEND_VITE_API_BASE_URL` from [`.env`](.env).
- Default frontend `X-Ingest-Key` can be injected at build time with `FRONTEND_VITE_DEFAULT_INGEST_KEY` (useful for local testing).

## Local demo ingestion key for frontend testing

- Seed utility in [`event_platform.infrastructure.db.seed`](src/event_platform/infrastructure/db/seed.py:46) creates tenant `demo-workspace` and defaults to key `ing_demo_workspace_local_key`.
- Default `.env` templates now set `FRONTEND_VITE_DEFAULT_INGEST_KEY=ing_demo_workspace_local_key` so Events/Aggregates pages can work immediately after seeding.
- If you rotate the key, update `FRONTEND_VITE_DEFAULT_INGEST_KEY` and rebuild frontend (`docker compose up --build`).

## Local development (without Docker)

```bash
python -m venv .venv
. .venv/Scripts/activate
pip install -e .[dev]
uvicorn event_platform.main:app --reload
```

## Repository layout

- `src/event_platform/` application package
- `docs/` architecture, API spec, ADRs
- `alembic/` migration scaffolding
- `tests/` baseline tests

## Milestone 2 database workflow

1. Install dependencies:

   ```bash
   pip install -e .[dev]
   ```

2. Configure DB env for local non-Docker runs (example):

   ```bash
   set POSTGRES_HOST=postgres
   set POSTGRES_PORT=5432
   set POSTGRES_DB=event_platform
   set POSTGRES_USER=event_platform
   set POSTGRES_PASSWORD=event_platform
   ```

3. Run migration cycle:

   ```bash
   alembic upgrade head
   alembic downgrade base
   alembic upgrade head
   ```

4. Seed demo tenant and ingestion key:

   ```bash
   python -m event_platform.infrastructure.db.seed
   ```

5. Run tests:

   ```bash
   pytest -q
   ```

