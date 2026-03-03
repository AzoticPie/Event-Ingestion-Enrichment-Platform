# API Specification Draft (Milestone 1)

## Base URL

- Local: `http://localhost:8000`

## Health endpoints

### `GET /health/live`

Liveness probe for process-level availability.

Response `200`:

```json
{
  "status": "ok"
}
```

### `GET /health/ready`

Readiness probe for dependency availability (PostgreSQL and Redis).

Response `200`:

```json
{
  "status": "ready",
  "dependencies": {
    "postgres": "ok",
    "redis": "ok"
  }
}
```

Response `503`:

```json
{
  "detail": {
    "status": "not_ready",
    "dependencies": {
      "postgres": "error: ...",
      "redis": "ok"
    }
  }
}
```

## Planned endpoint groups (next milestones)

- `POST /v1/ingest/events`
- `POST /v1/ingest/events:batch`
- `GET /v1/events`
- `GET /v1/events/{event_id}`
- `GET /v1/aggregates/*`

