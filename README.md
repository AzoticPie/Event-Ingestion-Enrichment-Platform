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

3. Validate health endpoints:

   - `GET http://localhost:8000/health/live`
   - `GET http://localhost:8000/health/ready`

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
   set POSTGRES_HOST=localhost
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

