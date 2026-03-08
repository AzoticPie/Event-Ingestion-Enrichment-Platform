# Event Ingestion & Enrichment Platform

Backend service for tenant-scoped event ingestion, asynchronous enrichment, and query/aggregate APIs.

## Current progress snapshot 

### Completed

- **Backend API routes are implemented and wired**: health/readiness, ingestion (single + batch), event query/detail, and aggregate endpoints are active in the FastAPI app.
- **Async worker pipelines are implemented**: Celery tasks exist for enrichment and rollup refresh/backfill flows, including queue routing and beat schedule wiring.
- **Database schema and migrations are in place through rollups**: Alembic revisions cover core tables, enrichment tables, query indexes, and rollup/coverage tables.
- **Frontend MVP pages are implemented**: Health, Ingestion, Events Explorer, Aggregates, and Settings pages are present and routed.
- **Automated test coverage is substantial** across integration and unit suites, including health, ingestion, query APIs, aggregate APIs, enrichment pipeline, repositories, seed workflow, and rollup scheduler/windowing/coverage behaviors.

### In progress

- **Rollup-backed aggregate reads are partially adopted by design**: count/top-event-types/top-urls can use rollups when window coverage exists and filters permit; direct-query fallback remains active for unsupported filter combinations.
- **`unique-users` remains direct-query** (not rollup-backed), consistent with the current implementation.

### Next (from existing repository plans)

- Continue executing the implementation plans already tracked in `plans/`, with focus on operational hardening and incremental aggregate/rollup improvements documented there.

## Tech stack

- Python 3.12+
- FastAPI
- PostgreSQL
- Redis
- SQLAlchemy 2.0
- Celery
- React + Vite (frontend)

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
- `alembic/` migration scripts (core, enrichment, query indexes, rollups)
- `tests/` integration and unit coverage for API, enrichment, repositories, and rollup logic

## Database workflow (migrations, seed, tests)

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

