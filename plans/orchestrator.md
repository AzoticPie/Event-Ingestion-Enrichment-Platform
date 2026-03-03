Planning phase completed. The system blueprint below defines product shape, architecture, data model direction, API surface, and delivery sequence before implementation.

## 1) Project summary
Event Ingestion & Enrichment Platform is a modular-monolith backend that accepts tenant-scoped events (single and batch), validates and deduplicates them, stores immutable raw payloads, asynchronously enriches them through a job pipeline, and exposes robust query and aggregate APIs for analytics, operations, and audit/security use cases. The design emphasizes production realism: explicit module boundaries, typed Python services, transactional correctness, observability, and operational readiness for local and CI workflows.

## 2) MVP scope
MVP is the smallest version that still demonstrates strong backend engineering depth.

- Multi-tenant ingestion with per-tenant API keys
- Single and batch event ingestion endpoints
- Required-field and structural validation for flexible semi-structured payloads
- Idempotency and dedupe using tenant + idempotency key and content hash fallback
- Raw payload persistence exactly as received
- Normalized searchable event record for core fields
- Async enrichment pipeline with retry handling for:
  - event name/timestamp normalization
  - user-agent parsing
  - URL/referrer parsing
  - GeoIP country-level enrichment
  - basic risk flags (bot and velocity-suspect)
- Query API with filters, sorting, and cursor pagination
- Aggregate API: counts, top event types, top URLs, unique users
- Structured logging, health/readiness endpoints, basic metrics endpoint
- Docker Compose local environment with Postgres, Redis, API, worker
- Alembic migrations, pytest baseline suite, ruff + mypy checks

Tradeoff: keep enrichment breadth moderate while proving async architecture quality and data modeling maturity.

## 3) Stretch goals
- Per-tenant schema registry and compatibility modes
- Dead-letter queue viewer and replay endpoint
- Alert rules engine for anomaly flags
- Materialized rollups and scheduled aggregate compaction
- JWT-protected admin APIs with role scopes
- OpenTelemetry exporter wiring and trace propagation end-to-end
- CI pipeline with migration smoke test + contract test matrix
- Optional minimal admin dashboard read APIs (backend-first)

Tradeoff: stretch features should only be added after MVP tests and observability are stable.

## 4) Recommended architecture
Architecture style: modular monolith with domain-oriented packages and explicit layering.

Core boundaries:
- API layer: request validation, auth extraction, response mapping
- Application layer: orchestration use-cases, transactions, idempotency decisions
- Domain layer: business rules and value objects, enrichment contracts
- Infrastructure layer: SQLAlchemy repositories, Redis integrations, external parsers
- Worker layer: asynchronous enrichment execution and retry/failure policies

Job queue choice: Celery with Redis broker/backend.

Why Celery:
- Strong production credibility for Python async job orchestration
- Mature retry primitives, routing, and operational ecosystem
- Good portfolio signaling for distributed worker concerns
- Works well with Redis already required by platform

Main data flow:
1) Ingestion request authenticated by tenant ingestion key.
2) API validates payload shape and maps to ingestion command.
3) Application service performs idempotency check in transaction.
4) Writes immutable raw record + normalized core record.
5) Emits enrichment job with event identifier.
6) Worker executes enrichment stages and writes enriched projection + flags.
7) Query APIs read normalized/enriched tables and rollups for aggregates.

Reliability model:
- At-least-once job execution with idempotent enrichment writes
- Retry with exponential backoff
- Failure terminal state persisted in failed enrichment table for inspection/replay

## 5) Proposed folder structure
Root-level structure:

- [`pyproject.toml`](pyproject.toml)
- [`docker-compose.yml`](docker-compose.yml)
- [`.env.example`](.env.example)
- [`README.md`](README.md)
- [`alembic.ini`](alembic.ini)
- [`alembic/env.py`](alembic/env.py)
- [`alembic/versions/`](alembic/versions/)
- [`docs/architecture.md`](docs/architecture.md)
- [`docs/api-spec.md`](docs/api-spec.md)
- [`docs/adr/0001-modular-monolith.md`](docs/adr/0001-modular-monolith.md)
- [`docs/adr/0002-celery-with-redis.md`](docs/adr/0002-celery-with-redis.md)
- [`src/event_platform/main.py`](src/event_platform/main.py)
- [`src/event_platform/core/config.py`](src/event_platform/core/config.py)
- [`src/event_platform/core/logging.py`](src/event_platform/core/logging.py)
- [`src/event_platform/core/security.py`](src/event_platform/core/security.py)
- [`src/event_platform/core/observability.py`](src/event_platform/core/observability.py)
- [`src/event_platform/api/dependencies.py`](src/event_platform/api/dependencies.py)
- [`src/event_platform/api/errors.py`](src/event_platform/api/errors.py)
- [`src/event_platform/api/routes/ingestion.py`](src/event_platform/api/routes/ingestion.py)
- [`src/event_platform/api/routes/events.py`](src/event_platform/api/routes/events.py)
- [`src/event_platform/api/routes/aggregates.py`](src/event_platform/api/routes/aggregates.py)
- [`src/event_platform/api/routes/health.py`](src/event_platform/api/routes/health.py)
- [`src/event_platform/domain/events/entities.py`](src/event_platform/domain/events/entities.py)
- [`src/event_platform/domain/events/value_objects.py`](src/event_platform/domain/events/value_objects.py)
- [`src/event_platform/domain/events/services.py`](src/event_platform/domain/events/services.py)
- [`src/event_platform/application/ingestion_service.py`](src/event_platform/application/ingestion_service.py)
- [`src/event_platform/application/query_service.py`](src/event_platform/application/query_service.py)
- [`src/event_platform/application/enrichment_service.py`](src/event_platform/application/enrichment_service.py)
- [`src/event_platform/infrastructure/db/models.py`](src/event_platform/infrastructure/db/models.py)
- [`src/event_platform/infrastructure/db/session.py`](src/event_platform/infrastructure/db/session.py)
- [`src/event_platform/infrastructure/repositories/events_repo.py`](src/event_platform/infrastructure/repositories/events_repo.py)
- [`src/event_platform/infrastructure/repositories/tenants_repo.py`](src/event_platform/infrastructure/repositories/tenants_repo.py)
- [`src/event_platform/infrastructure/enrichment/geoip.py`](src/event_platform/infrastructure/enrichment/geoip.py)
- [`src/event_platform/infrastructure/enrichment/user_agent.py`](src/event_platform/infrastructure/enrichment/user_agent.py)
- [`src/event_platform/infrastructure/enrichment/url_parser.py`](src/event_platform/infrastructure/enrichment/url_parser.py)
- [`src/event_platform/worker/celery_app.py`](src/event_platform/worker/celery_app.py)
- [`src/event_platform/worker/tasks/enrichment.py`](src/event_platform/worker/tasks/enrichment.py)
- [`tests/unit/test_ingestion_service.py`](tests/unit/test_ingestion_service.py)
- [`tests/integration/test_ingestion_api.py`](tests/integration/test_ingestion_api.py)
- [`tests/integration/test_query_api.py`](tests/integration/test_query_api.py)
- [`tests/worker/test_enrichment_tasks.py`](tests/worker/test_enrichment_tasks.py)

## 6) Core database tables
Core relational model (PostgreSQL):

- Tenant
  - id, name, status, created_at
  - indexes: name unique

- IngestionKey
  - id, tenant_id, key_prefix, key_hash, is_active, last_used_at, created_at
  - indexes: tenant_id, key_prefix unique, is_active

- EventRaw
  - id (uuid), tenant_id, source, event_type_original, occurred_at_original, received_at, payload_jsonb, headers_jsonb, ip, user_agent, idempotency_key, dedupe_hash, schema_version, ingest_status
  - indexes: tenant_id+received_at desc, tenant_id+idempotency_key unique (nullable strategy), tenant_id+dedupe_hash, tenant_id+event_type_original

- EventNormalized
  - event_id (fk to EventRaw.id), tenant_id, event_type_canonical, occurred_at_utc, user_id, session_id, severity, url, referrer, source, ingestion_date
  - indexes: tenant_id+occurred_at_utc desc, tenant_id+event_type_canonical+occurred_at_utc, tenant_id+user_id+occurred_at_utc

- EventEnriched
  - event_id, tenant_id, geo_country, geo_region, geo_city, ua_browser, ua_os, ua_device, url_host, url_path, referrer_domain, is_bot, unusual_geo, velocity_suspect, schema_tag, enriched_at
  - indexes: tenant_id+enriched_at desc, tenant_id+is_bot, tenant_id+geo_country, tenant_id+url_host

- AggregateRollup
  - id, tenant_id, bucket_start, bucket_granularity, metric_name, dimension_key, metric_value, updated_at
  - indexes: tenant_id+bucket_start+metric_name, tenant_id+metric_name+dimension_key

- FailedEnrichment
  - id, event_id, tenant_id, stage, error_code, error_message, attempts, failed_at, next_retry_at, status
  - indexes: tenant_id+status+failed_at, event_id unique

Idempotency strategy:
- Primary: tenant_id + idempotency_key uniqueness when key provided.
- Secondary: tenant_id + dedupe_hash on stable canonical subset (event_type, timestamp bucket, user/session key, normalized payload digest).
- Enrichment writes are upsert/idempotent keyed by event_id.

## 7) Initial API endpoints
Ingestion endpoints:
- POST /v1/ingest/events
- POST /v1/ingest/events:batch

Query endpoints:
- GET /v1/events
- GET /v1/events/{event_id}
- GET /v1/aggregates/count
- GET /v1/aggregates/top-event-types
- GET /v1/aggregates/top-urls
- GET /v1/aggregates/unique-users

Ops endpoints:
- GET /health/live
- GET /health/ready
- GET /metrics

Auth model:
- Ingestion endpoints: API key via header X-Ingest-Key mapped to tenant.
- Query/admin endpoints (MVP option A): internal-only + static admin token.
- Query/admin endpoints (MVP option B preferred): JWT bearer with tenant scope claim.

Request/response contract direction:
- Request carries event_type, occurred_at, source, user/session context, attributes map, optional idempotency_key.
- Batch request includes batch metadata and list of events.
- Response returns accepted ids, dedupe outcome, and processing status.

Pagination/filtering:
- Cursor pagination using occurred_at + event_id composite cursor.
- Filters: tenant scope, time range, event type, severity, user_id, source, flags.
- Sort: occurred_at asc/desc with stable tiebreaker event_id.

Error format:
- Uniform error envelope with code, message, details, request_id.
- Clear domain errors: auth_failed, tenant_scope_violation, validation_failed, idempotency_conflict, rate_limited, internal_error.

## 8) Implementation milestones
Milestone 1: Foundation and architecture artifacts
- Initialize project skeleton, dependency management, config, logging, health endpoints
- Add architecture doc, API spec draft, first ADRs
- Working increment: service boots in Docker, health checks pass

Milestone 2: Data model and migrations
- Implement SQLAlchemy models + Alembic migrations for tenant, keys, raw/normalized tables
- Create repository abstractions and DB session management
- Working increment: migration up/down successful, seed tenant/key

Milestone 3: Ingestion MVP
- Build API-key auth, single/batch ingestion routes, validation, idempotency logic
- Persist raw and normalized records transactionally
- Working increment: ingest and query basic event list

Milestone 4: Enrichment worker pipeline
- Introduce Celery worker, enrichment tasks, retries, failed enrichment persistence
- Add parser integrations (UA/URL/GeoIP baseline)
- Working increment: ingested events become enriched asynchronously

Milestone 5: Query and aggregates
- Implement filtered event queries with cursor pagination
- Implement aggregate endpoints with indexed queries and optional rollups
- Working increment: dashboard-ready read APIs

Milestone 6: Reliability and observability hardening
- Rate limiting, structured error handling, metrics, correlation IDs, retry policies
- Add readiness checks for DB/Redis and failure-path tests
- Working increment: operationally credible local stack

Milestone 7: Quality and delivery
- Expand pytest unit/integration/worker tests
- Enforce ruff, mypy, and CI workflow
- Finalize README, runbook notes, architecture diagrams, ADR updates
- Working increment: portfolio-grade repository ready for review

Decision checkpoint reached: architecture-first plan is complete and coding can begin in milestone order without ambiguity.