# Milestone 3: Ingestion MVP (Implemented Details)

## Milestone objective and delivered increment

Milestone 3 objective: deliver a tenant-scoped ingestion MVP with API-key authentication, single/batch ingest endpoints, validation, idempotency/dedupe behavior, transactional persistence of raw+normalized records, and a basic event list query.

Delivered increment in this codebase:
- Authenticated tenant resolution from `X-Ingest-Key` and tenant context injection via [`get_authenticated_tenant()`](src/event_platform/api/dependencies.py:24)
- Ingestion routes for single and batch requests in [`ingestion.py`](src/event_platform/api/routes/ingestion.py)
- Event list route in [`list_events()`](src/event_platform/api/routes/events.py:17)
- Idempotent ingest logic and dedupe hashing in [`IngestionService.ingest_event()`](src/event_platform/application/ingestion_service.py:31)
- Raw+normalized persistence through repositories in [`EventRawRepository.create()`](src/event_platform/infrastructure/repositories/events_repo.py:21) and [`EventNormalizedRepository.create()`](src/event_platform/infrastructure/repositories/events_repo.py:95)
- Query/list composition in [`QueryService.list_events()`](src/event_platform/application/query_service.py:15)

## Implemented endpoints and request/response behavior

### `POST /v1/ingest/events`
- Implemented in [`ingest_event()`](src/event_platform/api/routes/ingestion.py:34)
- Request model: [`IngestEventRequest`](src/event_platform/api/schemas/ingestion.py:12)
  - Includes required `event_type`, `occurred_at`, optional enrichment/idempotency fields, and `attributes`
- Response model/status:
  - [`IngestSingleResponse`](src/event_platform/api/schemas/ingestion.py:43)
  - HTTP `202 Accepted` from route declaration in [`ingestion.py`](src/event_platform/api/routes/ingestion.py:33)
  - Payload includes `event_id`, `status` (`accepted|duplicate`), optional `duplicate_reason`

### `POST /v1/ingest/events:batch`
- Implemented in [`ingest_events_batch()`](src/event_platform/api/routes/ingestion.py:64)
- Request model: [`IngestBatchRequest`](src/event_platform/api/schemas/ingestion.py:28)
  - `events` constrained to `1..1000` items
- Response model/status:
  - [`IngestBatchResponse`](src/event_platform/api/schemas/ingestion.py:49)
  - HTTP `202 Accepted` from route declaration in [`ingestion.py`](src/event_platform/api/routes/ingestion.py:63)
  - Returns `total_count`, `accepted_count`, `duplicate_count`, and per-event results

### `GET /v1/events`
- Implemented in [`list_events()`](src/event_platform/api/routes/events.py:17)
- Query params:
  - `limit` default `50`, min `1`, max `200` in [`events.py`](src/event_platform/api/routes/events.py:18)
  - optional `event_type` filter in [`events.py`](src/event_platform/api/routes/events.py:19)
- Response model:
  - [`EventListResponse`](src/event_platform/api/schemas/events.py:27) containing `count` and `items`

## API-key auth flow (header, lookup, verification, tenant scoping)

- Header usage: route dependencies read `X-Ingest-Key` via [`Header(alias="X-Ingest-Key")`](src/event_platform/api/dependencies.py:25)
- Prefix lookup: key prefix derived by [`ingestion_key_prefix()`](src/event_platform/core/security.py:9), then active key fetched with [`find_active_by_prefix()`](src/event_platform/infrastructure/repositories/keys_repo.py:37)
- Hash verification: constant-time check in [`verify_ingestion_key()`](src/event_platform/core/security.py:19)
- Failure behavior: invalid/missing key path raises HTTP `401` with `{"code":"auth_failed"...}` in [`dependencies.py`](src/event_platform/api/dependencies.py:33)
- Tenant scoping: successful auth returns [`AuthContext`](src/event_platform/api/dependencies.py:17) with `tenant_id`; that tenant id is passed into ingest/query services in [`ingestion.py`](src/event_platform/api/routes/ingestion.py:47) and [`events.py`](src/event_platform/api/routes/events.py:27)

## Idempotency and dedupe behavior

- UTC normalization of event time in [`_ensure_utc()`](src/event_platform/application/ingestion_service.py:117)
- Dedupe hash construction in [`_build_dedupe_hash()`](src/event_platform/application/ingestion_service.py:123)
  - Hash material includes canonicalized `event_type`, timestamp, source, identity/session fields, severity/url/referrer, schema version, and attributes
- Duplicate checks in [`IngestionService.ingest_event()`](src/event_platform/application/ingestion_service.py:31):
  1. If `idempotency_key` provided, lookup by tenant+idempotency key via [`find_by_idempotency_key()`](src/event_platform/infrastructure/repositories/events_repo.py:54)
  2. Lookup by tenant+dedupe hash via [`find_by_dedupe_hash()`](src/event_platform/infrastructure/repositories/events_repo.py:61)
- Duplicate outcomes return existing `event_id` with status `duplicate` and reason `idempotency_key` or `dedupe_hash` in [`ingestion_service.py`](src/event_platform/application/ingestion_service.py:60)

## Transactional persistence path (raw + normalized)

- Route-level transaction boundary wraps ingest operations using [`transaction()`](src/event_platform/infrastructure/db/session.py:48) in both single and batch routes ([`ingestion.py`](src/event_platform/api/routes/ingestion.py:44), [`ingestion.py`](src/event_platform/api/routes/ingestion.py:75))
- Accepted event write path in [`IngestionService.ingest_event()`](src/event_platform/application/ingestion_service.py:74):
  - Raw event inserted first via [`EventRawRepository.create()`](src/event_platform/infrastructure/repositories/events_repo.py:21)
  - Normalized projection inserted second via [`EventNormalizedRepository.create()`](src/event_platform/infrastructure/repositories/events_repo.py:95)
- Raw persistence includes payload JSON, sanitized headers, idempotency metadata, dedupe hash, IP and user-agent fields (see [`ingestion.py`](src/event_platform/api/routes/ingestion.py:104) and [`ingestion_service.py`](src/event_platform/application/ingestion_service.py:79))
- Header sanitation excludes sensitive names including `x-ingest-key` via [`SENSITIVE_HEADER_NAMES`](src/event_platform/api/routes/ingestion.py:23)

## Basic query/list behavior

- Query route calls [`QueryService.list_events()`](src/event_platform/application/query_service.py:15)
- Repository-level query joins raw+normalized records in [`list_with_normalized()`](src/event_platform/infrastructure/repositories/events_repo.py:68)
  - Enforces tenant filter
  - Optional canonicalized `event_type` filter
  - Sorted by newest `occurred_at_utc` then `id`
  - Limited by `limit`
- Response fields are mapped to [`EventListItem`](src/event_platform/api/schemas/events.py:11)

## Test coverage and latest validation status

Primary ingestion integration coverage is in [`tests/integration/test_ingestion_api.py`](tests/integration/test_ingestion_api.py):
- End-to-end single ingest + list query flow in [`test_single_ingestion_and_event_list_flow()`](tests/integration/test_ingestion_api.py:23)
- Idempotency replay duplicate behavior in [`test_idempotency_duplicate_flow()`](tests/integration/test_ingestion_api.py:99)
- Dedupe hash behavior across extended payload fields in [`test_dedupe_hash_distinguishes_extended_payload_fields()`](tests/integration/test_ingestion_api.py:160)
- Header redaction assertion (`x-ingest-key` absent from persisted headers) in [`test_ingestion_api.py`](tests/integration/test_ingestion_api.py:79)

Latest validation status (provided): `pytest -q` => **1 passed, 5 skipped**.

## Known environment caveat

DB-dependent integration tests are intentionally skipped when PostgreSQL is unavailable:
- Explicit DB availability guard and skip in [`_db_available()`](tests/integration/test_ingestion_api.py:13) and call sites ([`test_ingestion_api.py`](tests/integration/test_ingestion_api.py:24), [`test_ingestion_api.py`](tests/integration/test_ingestion_api.py:100), [`test_ingestion_api.py`](tests/integration/test_ingestion_api.py:161))
- Similar skip pattern exists in other integration tests, e.g. [`test_migration_smoke.py`](tests/integration/test_migration_smoke.py:19), [`test_repositories.py`](tests/integration/test_repositories.py:20), [`test_seed.py`](tests/integration/test_seed.py:15)
