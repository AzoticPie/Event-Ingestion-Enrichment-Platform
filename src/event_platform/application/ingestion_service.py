"""Ingestion use-cases for single and batch event persistence."""

from __future__ import annotations

import hashlib
import json
import uuid
from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Any

from sqlalchemy.orm import Session

from event_platform.core.normalization import canonical_event_type
from event_platform.api.schemas.ingestion import IngestEventRequest
from event_platform.infrastructure.repositories.events_repo import EventNormalizedRepository, EventRawRepository


@dataclass(slots=True)
class IngestionResult:
    """Result of a single ingest operation."""

    event_id: uuid.UUID
    status: str
    duplicate_reason: str | None = None
    queued_for_enrichment: bool = False


class IngestionService:
    """Service encapsulating idempotent event ingestion rules."""

    def ingest_event(
        self,
        session: Session,
        tenant_id: uuid.UUID,
        payload: IngestEventRequest,
        headers_jsonb: dict[str, Any],
        ip: str | None,
        user_agent: str | None,
    ) -> IngestionResult:
        raw_repo = EventRawRepository(session)
        normalized_repo = EventNormalizedRepository(session)

        occurred_at_utc = _ensure_utc(payload.occurred_at)
        dedupe_hash = _build_dedupe_hash(
            event_type=payload.event_type,
            occurred_at=occurred_at_utc,
            source=payload.source,
            user_id=payload.user_id,
            session_id=payload.session_id,
            severity=payload.severity,
            url=payload.url,
            referrer=payload.referrer,
            schema_version=payload.schema_version,
            attributes=payload.attributes,
        )

        if payload.idempotency_key:
            existing_by_key = raw_repo.find_by_idempotency_key(tenant_id, payload.idempotency_key)
            if existing_by_key is not None:
                return IngestionResult(
                    event_id=existing_by_key.id,
                    status="duplicate",
                    duplicate_reason="idempotency_key",
                    queued_for_enrichment=False,
                )

        existing_by_hash = raw_repo.find_by_dedupe_hash(tenant_id, dedupe_hash)
        if existing_by_hash is not None:
            return IngestionResult(
                event_id=existing_by_hash.id,
                status="duplicate",
                duplicate_reason="dedupe_hash",
                queued_for_enrichment=False,
            )

        event_raw = raw_repo.create(
            tenant_id=tenant_id,
            source=payload.source,
            event_type_original=payload.event_type,
            occurred_at_original=occurred_at_utc,
            payload_jsonb={
                "event_type": payload.event_type,
                "occurred_at": occurred_at_utc.isoformat(),
                "source": payload.source,
                "user_id": payload.user_id,
                "session_id": payload.session_id,
                "severity": payload.severity,
                "url": payload.url,
                "referrer": payload.referrer,
                "attributes": payload.attributes,
                "schema_version": payload.schema_version,
            },
            headers_jsonb=headers_jsonb,
            idempotency_key=payload.idempotency_key,
            dedupe_hash=dedupe_hash,
            ip=ip,
            user_agent=user_agent,
            schema_version=payload.schema_version,
            ingest_status="accepted",
        )

        normalized_repo.create(
            event_id=event_raw.id,
            tenant_id=tenant_id,
            event_type_canonical=canonical_event_type(payload.event_type),
            occurred_at_utc=occurred_at_utc,
            user_id=payload.user_id,
            session_id=payload.session_id,
            severity=payload.severity,
            url=payload.url,
            referrer=payload.referrer,
            source=payload.source,
            ingestion_date=occurred_at_utc.date(),
        )

        return IngestionResult(event_id=event_raw.id, status="accepted", queued_for_enrichment=True)


def _ensure_utc(value: datetime) -> datetime:
    if value.tzinfo is None:
        return value.replace(tzinfo=UTC)
    return value.astimezone(UTC)


def _build_dedupe_hash(
    event_type: str,
    occurred_at: datetime,
    source: str,
    user_id: str | None,
    session_id: str | None,
    severity: str | None,
    url: str | None,
    referrer: str | None,
    schema_version: str | None,
    attributes: dict[str, Any],
) -> str:
    material = {
        "event_type": canonical_event_type(event_type),
        "occurred_at": occurred_at.isoformat(),
        "source": source,
        "user_id": user_id,
        "session_id": session_id,
        "severity": severity,
        "url": url,
        "referrer": referrer,
        "schema_version": schema_version,
        "attributes": attributes,
    }
    digest_input = json.dumps(material, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(digest_input.encode("utf-8")).hexdigest()

