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

