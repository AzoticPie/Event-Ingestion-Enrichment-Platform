# Architecture (Milestone 1)

## High-level design

The platform is a modular monolith built with FastAPI, SQLAlchemy, PostgreSQL, Redis, and Celery. The API process handles ingestion and query concerns, while Celery workers execute asynchronous enrichment jobs.

### Layering

- API layer: request/response contracts and route composition
- Application layer: use-case orchestration and transaction management
- Domain layer: event rules, dedupe, and validation semantics
- Infrastructure layer: persistence adapters and external integrations
- Worker layer: asynchronous enrichment pipeline and retries

## Runtime topology

- `api` container: FastAPI application
- `worker` container: Celery worker process
- `postgres` container: relational storage
- `redis` container: broker/cache for worker jobs

## Data flow (MVP direction)

1. Client posts single or batch events with an ingestion API key.
2. API validates payload, applies idempotency checks, persists raw + normalized records.
3. API enqueues enrichment task(s) in Redis via Celery.
4. Worker enriches events and stores enrichment projection.
5. Query endpoints read normalized and enriched views.

## Operational baseline in this milestone

- Environment-driven configuration
- Structured JSON logs
- `/health/live` and `/health/ready` probes
- Docker Compose orchestration for local setup

