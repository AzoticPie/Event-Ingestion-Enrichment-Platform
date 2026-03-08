"""Repositories for event write/read models and aggregates."""

from __future__ import annotations

import uuid
from datetime import UTC, date, datetime

from sqlalchemy import Select, and_, asc, desc, distinct, func, or_, select
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

    def list_filtered_page(
        self,
        tenant_id: uuid.UUID,
        limit: int,
        sort: str,
        cursor_occurred_at: datetime | None,
        cursor_event_id: uuid.UUID | None,
        occurred_from: datetime | None,
        occurred_to: datetime | None,
        event_type: str | None,
        severity: str | None,
        source: str | None,
        user_id: str | None,
        session_id: str | None,
        ingest_status: str | None,
        geo_country: str | None,
        is_bot: bool | None,
    ) -> list[tuple[EventRaw, EventNormalized]]:
        stmt: Select[tuple[EventRaw, EventNormalized]] = (
            select(EventRaw, EventNormalized)
            .join(EventNormalized, EventNormalized.event_id == EventRaw.id)
            .outerjoin(EventEnriched, EventEnriched.event_id == EventRaw.id)
            .options(selectinload(EventRaw.enriched))
            .where(EventRaw.tenant_id == tenant_id)
        )

        stmt = _apply_common_filters(
            stmt=stmt,
            occurred_from=occurred_from,
            occurred_to=occurred_to,
            event_type=event_type,
            severity=severity,
            source=source,
            user_id=user_id,
            session_id=session_id,
            ingest_status=ingest_status,
            geo_country=geo_country,
            is_bot=is_bot,
        )

        if cursor_occurred_at is not None and cursor_event_id is not None:
            if sort == "asc":
                stmt = stmt.where(
                    or_(
                        EventNormalized.occurred_at_utc > cursor_occurred_at,
                        and_(
                            EventNormalized.occurred_at_utc == cursor_occurred_at,
                            EventRaw.id > cursor_event_id,
                        ),
                    )
                )
            else:
                stmt = stmt.where(
                    or_(
                        EventNormalized.occurred_at_utc < cursor_occurred_at,
                        and_(
                            EventNormalized.occurred_at_utc == cursor_occurred_at,
                            EventRaw.id < cursor_event_id,
                        ),
                    )
                )

        if sort == "asc":
            stmt = stmt.order_by(asc(EventNormalized.occurred_at_utc), asc(EventRaw.id))
        else:
            stmt = stmt.order_by(desc(EventNormalized.occurred_at_utc), desc(EventRaw.id))

        stmt = stmt.limit(limit + 1)
        rows = self._session.execute(stmt).all()
        return [(raw, normalized) for raw, normalized in rows]

    def get_event_detail(self, tenant_id: uuid.UUID, event_id: uuid.UUID) -> tuple[EventRaw, EventNormalized] | None:
        stmt = (
            select(EventRaw, EventNormalized)
            .join(EventNormalized, EventNormalized.event_id == EventRaw.id)
            .options(selectinload(EventRaw.enriched))
            .where(EventRaw.id == event_id, EventRaw.tenant_id == tenant_id)
        )
        row = self._session.execute(stmt).one_or_none()
        if row is None:
            return None
        raw, normalized = row
        return raw, normalized

    def count_events(
        self,
        tenant_id: uuid.UUID,
        occurred_from: datetime | None,
        occurred_to: datetime | None,
        event_type: str | None,
        severity: str | None,
        source: str | None,
        user_id: str | None,
        session_id: str | None,
        ingest_status: str | None,
        geo_country: str | None,
        is_bot: bool | None,
    ) -> int:
        stmt: Select[tuple[int]] = (
            select(func.count())
            .select_from(EventRaw)
            .join(EventNormalized, EventNormalized.event_id == EventRaw.id)
            .outerjoin(EventEnriched, EventEnriched.event_id == EventRaw.id)
            .where(EventRaw.tenant_id == tenant_id)
        )
        stmt = _apply_common_filters(
            stmt=stmt,
            occurred_from=occurred_from,
            occurred_to=occurred_to,
            event_type=event_type,
            severity=severity,
            source=source,
            user_id=user_id,
            session_id=session_id,
            ingest_status=ingest_status,
            geo_country=geo_country,
            is_bot=is_bot,
        )
        value = self._session.execute(stmt).scalar_one()
        return int(value)

    def top_event_types(
        self,
        tenant_id: uuid.UUID,
        limit: int,
        occurred_from: datetime | None,
        occurred_to: datetime | None,
        source: str | None,
        severity: str | None,
        geo_country: str | None,
        is_bot: bool | None,
    ) -> list[tuple[str, int]]:
        stmt: Select[tuple[str, int]] = (
            select(EventNormalized.event_type_canonical, func.count().label("value"))
            .select_from(EventRaw)
            .join(EventNormalized, EventNormalized.event_id == EventRaw.id)
            .outerjoin(EventEnriched, EventEnriched.event_id == EventRaw.id)
            .where(EventRaw.tenant_id == tenant_id)
            .group_by(EventNormalized.event_type_canonical)
            .order_by(desc("value"), asc(EventNormalized.event_type_canonical))
            .limit(limit)
        )

        stmt = _apply_common_filters(
            stmt=stmt,
            occurred_from=occurred_from,
            occurred_to=occurred_to,
            event_type=None,
            severity=severity,
            source=source,
            user_id=None,
            session_id=None,
            ingest_status=None,
            geo_country=geo_country,
            is_bot=is_bot,
        )
        rows = self._session.execute(stmt).all()
        return [(event_type_name, int(value)) for event_type_name, value in rows]

    def top_urls(
        self,
        tenant_id: uuid.UUID,
        limit: int,
        occurred_from: datetime | None,
        occurred_to: datetime | None,
        event_type: str | None,
        source: str | None,
        severity: str | None,
        geo_country: str | None,
        is_bot: bool | None,
    ) -> list[tuple[str, int]]:
        stmt: Select[tuple[str, int]] = (
            select(EventEnriched.url_host, func.count().label("value"))
            .select_from(EventRaw)
            .join(EventNormalized, EventNormalized.event_id == EventRaw.id)
            .join(EventEnriched, EventEnriched.event_id == EventRaw.id)
            .where(EventRaw.tenant_id == tenant_id)
            .where(EventEnriched.url_host.is_not(None))
            .where(func.length(func.btrim(EventEnriched.url_host)) > 0)
            .group_by(EventEnriched.url_host)
            .order_by(desc("value"), asc(EventEnriched.url_host))
            .limit(limit)
        )
        stmt = _apply_common_filters(
            stmt=stmt,
            occurred_from=occurred_from,
            occurred_to=occurred_to,
            event_type=event_type,
            severity=severity,
            source=source,
            user_id=None,
            session_id=None,
            ingest_status=None,
            geo_country=geo_country,
            is_bot=is_bot,
        )
        rows = self._session.execute(stmt).all()
        return [(url_host, int(value)) for url_host, value in rows if isinstance(url_host, str)]

    def unique_users(
        self,
        tenant_id: uuid.UUID,
        occurred_from: datetime | None,
        occurred_to: datetime | None,
        event_type: str | None,
        source: str | None,
        severity: str | None,
        geo_country: str | None,
        is_bot: bool | None,
    ) -> int:
        stmt: Select[tuple[int]] = (
            select(func.count(distinct(EventNormalized.user_id)))
            .select_from(EventRaw)
            .join(EventNormalized, EventNormalized.event_id == EventRaw.id)
            .outerjoin(EventEnriched, EventEnriched.event_id == EventRaw.id)
            .where(EventRaw.tenant_id == tenant_id)
            .where(EventNormalized.user_id.is_not(None))
        )
        stmt = _apply_common_filters(
            stmt=stmt,
            occurred_from=occurred_from,
            occurred_to=occurred_to,
            event_type=event_type,
            severity=severity,
            source=source,
            user_id=None,
            session_id=None,
            ingest_status=None,
            geo_country=geo_country,
            is_bot=is_bot,
        )
        value = self._session.execute(stmt).scalar_one()
        return int(value)


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


def _apply_common_filters(
    stmt: Select,
    occurred_from: datetime | None,
    occurred_to: datetime | None,
    event_type: str | None,
    severity: str | None,
    source: str | None,
    user_id: str | None,
    session_id: str | None,
    ingest_status: str | None,
    geo_country: str | None,
    is_bot: bool | None,
) -> Select:
    if occurred_from is not None:
        stmt = stmt.where(EventNormalized.occurred_at_utc >= occurred_from)
    if occurred_to is not None:
        stmt = stmt.where(EventNormalized.occurred_at_utc <= occurred_to)
    if event_type:
        stmt = stmt.where(EventNormalized.event_type_canonical == canonical_event_type(event_type))
    if severity:
        stmt = stmt.where(EventNormalized.severity == severity)
    if source:
        stmt = stmt.where(EventNormalized.source == source)
    if user_id:
        stmt = stmt.where(EventNormalized.user_id == user_id)
    if session_id:
        stmt = stmt.where(EventNormalized.session_id == session_id)
    if ingest_status:
        stmt = stmt.where(EventRaw.ingest_status == ingest_status)
    if geo_country:
        stmt = stmt.where(EventEnriched.geo_country == geo_country)
    if is_bot is True:
        stmt = stmt.where(EventEnriched.is_bot.is_(True))
    elif is_bot is False:
        stmt = stmt.where(or_(EventEnriched.is_bot.is_(False), EventEnriched.event_id.is_(None)))
    return stmt

