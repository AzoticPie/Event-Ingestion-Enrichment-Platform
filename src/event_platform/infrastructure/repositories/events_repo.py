"""Event repositories for raw and normalized event records."""

from __future__ import annotations

import uuid
from datetime import date, datetime

from sqlalchemy import select
from sqlalchemy.orm import Session

from event_platform.core.normalization import canonical_event_type
from event_platform.infrastructure.db.models import EventNormalized, EventRaw


class EventRawRepository:
    """Data access for immutable raw events."""

    def __init__(self, session: Session) -> None:
        self._session = session

    def create(
        self,
        tenant_id: uuid.UUID,
        source: str,
        event_type_original: str,
        occurred_at_original: datetime,
        payload_jsonb: dict[str, object],
        headers_jsonb: dict[str, object] | None,
        dedupe_hash: str,
        idempotency_key: str | None = None,
        ip: str | None = None,
        user_agent: str | None = None,
        schema_version: str | None = None,
        ingest_status: str = "accepted",
    ) -> EventRaw:
        event = EventRaw(
            tenant_id=tenant_id,
            source=source,
            event_type_original=event_type_original,
            occurred_at_original=occurred_at_original,
            payload_jsonb=payload_jsonb,
            headers_jsonb=headers_jsonb or {},
            idempotency_key=idempotency_key,
            dedupe_hash=dedupe_hash,
            ip=ip,
            user_agent=user_agent,
            schema_version=schema_version,
            ingest_status=ingest_status,
        )
        self._session.add(event)
        self._session.flush()
        return event

    def find_by_idempotency_key(self, tenant_id: uuid.UUID, idempotency_key: str) -> EventRaw | None:
        stmt = select(EventRaw).where(
            EventRaw.tenant_id == tenant_id,
            EventRaw.idempotency_key == idempotency_key,
        )
        return self._session.execute(stmt).scalar_one_or_none()

    def find_by_dedupe_hash(self, tenant_id: uuid.UUID, dedupe_hash: str) -> EventRaw | None:
        stmt = select(EventRaw).where(
            EventRaw.tenant_id == tenant_id,
            EventRaw.dedupe_hash == dedupe_hash,
        )
        return self._session.execute(stmt).scalar_one_or_none()

    def list_with_normalized(
        self,
        tenant_id: uuid.UUID,
        limit: int,
        event_type: str | None,
    ) -> list[tuple[EventRaw, EventNormalized]]:
        stmt = (
            select(EventRaw, EventNormalized)
            .join(EventNormalized, EventNormalized.event_id == EventRaw.id)
            .where(EventRaw.tenant_id == tenant_id)
            .order_by(EventNormalized.occurred_at_utc.desc(), EventRaw.id.desc())
            .limit(limit)
        )

        if event_type is not None:
            stmt = stmt.where(EventNormalized.event_type_canonical == canonical_event_type(event_type))

        rows = self._session.execute(stmt).all()
        return [(raw, normalized) for raw, normalized in rows]


class EventNormalizedRepository:
    """Data access for normalized event projections."""

    def __init__(self, session: Session) -> None:
        self._session = session

    def create(
        self,
        event_id: uuid.UUID,
        tenant_id: uuid.UUID,
        event_type_canonical: str,
        occurred_at_utc: datetime,
        source: str,
        ingestion_date: date,
        user_id: str | None = None,
        session_id: str | None = None,
        severity: str | None = None,
        url: str | None = None,
        referrer: str | None = None,
    ) -> EventNormalized:
        normalized = EventNormalized(
            event_id=event_id,
            tenant_id=tenant_id,
            event_type_canonical=event_type_canonical,
            occurred_at_utc=occurred_at_utc,
            user_id=user_id,
            session_id=session_id,
            severity=severity,
            url=url,
            referrer=referrer,
            source=source,
            ingestion_date=ingestion_date,
        )
        self._session.add(normalized)
        self._session.flush()
        return normalized

    def get_by_event_id(self, event_id: uuid.UUID) -> EventNormalized | None:
        return self._session.get(EventNormalized, event_id)

