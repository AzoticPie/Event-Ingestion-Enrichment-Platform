# ADR-0002: Use Celery with Redis for Background Enrichment

## Status

Accepted

## Context

The platform requires asynchronous enrichment with retries and credible production-style worker patterns.

## Decision

Use Celery as the task queue and Redis as broker/result backend.

## Consequences

- Pros: mature retry controls, broad ecosystem, strong signaling for backend interviews
- Pros: straightforward Docker Compose integration
- Cons: additional moving parts and operational overhead compared to in-process jobs

