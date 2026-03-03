# ADR-0001: Adopt Modular Monolith Architecture

## Status

Accepted

## Context

The project needs portfolio-grade backend depth with realistic complexity, while remaining implementable by a solo developer.

## Decision

Use a modular monolith with explicit boundaries between API, application, domain, infrastructure, and worker concerns.

## Consequences

- Pros: simpler deployment, clear package boundaries, easier local development
- Pros: supports gradual extraction to services if needed later
- Cons: strict module discipline required to avoid architectural erosion

