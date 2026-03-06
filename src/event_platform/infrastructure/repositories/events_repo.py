"""Event repositories for raw and normalized event records."""

from __future__ import annotations

import uuid
from datetime import UTC, date, datetime

from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from event_platform.core.normalization import canonical_event_type
from event_platform.infrastructure.db.models import EventEnriched, EventNormalized, EventRaw, FailedEnrichment


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
            .options(selectinload(EventRaw.enriched))
            .where(EventRaw.tenant_id == tenant_id)
            .order_by(EventNormalized.occurred_at_utc.desc(), EventRaw.id.desc())
            .limit(limit)
        )

        if event_type is not None:
            stmt = stmt.where(EventNormalized.event_type_canonical == canonical_event_type(event_type))

        rows = self._session.execute(stmt).all()
        return [(raw, normalized) for raw, normalized in rows]


class EventRepository:
    """Combined data access for raw, normalized, enriched and failures."""

    def __init__(self, session: Session) -> None:
        self._session = session

    def get_raw_with_normalized(self, event_id: uuid.UUID) -> tuple[EventRaw, EventNormalized] | None:
        stmt = (
            select(EventRaw, EventNormalized)
            .join(EventNormalized, EventNormalized.event_id == EventRaw.id)
            .where(EventRaw.id == event_id)
        )
        row = self._session.execute(stmt).one_or_none()
        if row is None:
            return None
        raw, normalized = row
        return raw, normalized

    def get_enriched(self, event_id: uuid.UUID) -> EventEnriched | None:
        return self._session.get(EventEnriched, event_id)

    def upsert_enriched(
        self,
        event_id: uuid.UUID,
        tenant_id: uuid.UUID,
        geo_country: str | None,
        ua_browser: str | None,
        ua_os: str | None,
        ua_device: str | None,
        url_host: str | None,
        url_path: str | None,
        referrer_domain: str | None,
        is_bot: bool,
        schema_tag: str,
    ) -> EventEnriched:
        enriched = self._session.get(EventEnriched, event_id)
        if enriched is None:
            enriched = EventEnriched(
                event_id=event_id,
                tenant_id=tenant_id,
                geo_country=geo_country,
                ua_browser=ua_browser,
                ua_os=ua_os,
                ua_device=ua_device,
                url_host=url_host,
                url_path=url_path,
                referrer_domain=referrer_domain,
                is_bot=is_bot,
                schema_tag=schema_tag,
            )
            self._session.add(enriched)
        else:
            enriched.geo_country = geo_country
            enriched.ua_browser = ua_browser
            enriched.ua_os = ua_os
            enriched.ua_device = ua_device
            enriched.url_host = url_host
            enriched.url_path = url_path
            enriched.referrer_domain = referrer_domain
            enriched.is_bot = is_bot
            enriched.schema_tag = schema_tag
            enriched.enriched_at = datetime.now(UTC)

        self._session.flush()
        return enriched

    def upsert_failed_enrichment(
        self,
        event_id: uuid.UUID,
        tenant_id: uuid.UUID,
        stage: str,
        error_code: str,
        error_message: str,
        attempts: int,
        failed_at: datetime,
        next_retry_at: datetime | None,
        status: str,
        last_task_id: str | None,
    ) -> FailedEnrichment:
        record = self._session.execute(
            select(FailedEnrichment).where(FailedEnrichment.event_id == event_id)
        ).scalar_one_or_none()

        if record is None:
            record = FailedEnrichment(
                event_id=event_id,
                tenant_id=tenant_id,
                stage=stage,
                error_code=error_code,
                error_message=error_message,
                attempts=attempts,
                failed_at=failed_at,
                next_retry_at=next_retry_at,
                status=status,
                last_task_id=last_task_id,
            )
            self._session.add(record)
        else:
            record.stage = stage
            record.error_code = error_code
            record.error_message = error_message
            record.attempts = attempts
            record.failed_at = failed_at
            record.next_retry_at = next_retry_at
            record.status = status
            record.last_task_id = last_task_id

        self._session.flush()
        return record

    def clear_failed_enrichment(self, event_id: uuid.UUID) -> None:
        record = self._session.execute(
            select(FailedEnrichment).where(FailedEnrichment.event_id == event_id)
        ).scalar_one_or_none()
        if record is not None:
            self._session.delete(record)
            self._session.flush()

    def set_ingest_status(self, event_id: uuid.UUID, status: str) -> None:
        raw = self._session.get(EventRaw, event_id)
        if raw is not None:
            raw.ingest_status = status
            self._session.flush()


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

