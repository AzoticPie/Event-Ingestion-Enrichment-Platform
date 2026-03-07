"""Aggregate read use-cases for dashboard-style endpoints."""

from __future__ import annotations

import uuid
from datetime import UTC, datetime

from sqlalchemy.orm import Session

from event_platform.application.query_service import QueryValidationError
from event_platform.infrastructure.repositories.events_repo import EventRawRepository


def _to_utc(value: datetime | None) -> datetime | None:
    if value is None:
        return None
    if value.tzinfo is None:
        return value.replace(tzinfo=UTC)
    return value.astimezone(UTC)


def _normalize_window(occurred_from: datetime | None, occurred_to: datetime | None) -> tuple[datetime | None, datetime | None]:
    occurred_from_utc = _to_utc(occurred_from)
    occurred_to_utc = _to_utc(occurred_to)
    if occurred_from_utc and occurred_to_utc and occurred_from_utc > occurred_to_utc:
        raise QueryValidationError("occurred_from must be <= occurred_to")
    return occurred_from_utc, occurred_to_utc


class AggregateService:
    """Service providing aggregate read models."""

    def count_events(
        self,
        session: Session,
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
    ) -> dict[str, object]:
        occurred_from_utc, occurred_to_utc = _normalize_window(occurred_from, occurred_to)

        repo = EventRawRepository(session)
        value = repo.count_events(
            tenant_id=tenant_id,
            occurred_from=occurred_from_utc,
            occurred_to=occurred_to_utc,
            event_type=event_type,
            severity=severity,
            source=source,
            user_id=user_id,
            session_id=session_id,
            ingest_status=ingest_status,
            geo_country=geo_country,
            is_bot=is_bot,
        )
        return {"value": value, "data_source": "direct_query"}

    def top_event_types(
        self,
        session: Session,
        tenant_id: uuid.UUID,
        limit: int,
        occurred_from: datetime | None,
        occurred_to: datetime | None,
        source: str | None,
        severity: str | None,
        geo_country: str | None,
        is_bot: bool | None,
    ) -> dict[str, object]:
        occurred_from_utc, occurred_to_utc = _normalize_window(occurred_from, occurred_to)

        repo = EventRawRepository(session)
        rows = repo.top_event_types(
            tenant_id=tenant_id,
            limit=limit,
            occurred_from=occurred_from_utc,
            occurred_to=occurred_to_utc,
            source=source,
            severity=severity,
            geo_country=geo_country,
            is_bot=is_bot,
        )
        items = [{"key": key, "value": value} for key, value in rows]
        return {"items": items, "data_source": "direct_query"}

    def top_urls(
        self,
        session: Session,
        tenant_id: uuid.UUID,
        limit: int,
        occurred_from: datetime | None,
        occurred_to: datetime | None,
        event_type: str | None,
        source: str | None,
        severity: str | None,
        geo_country: str | None,
        is_bot: bool | None,
    ) -> dict[str, object]:
        occurred_from_utc, occurred_to_utc = _normalize_window(occurred_from, occurred_to)

        repo = EventRawRepository(session)
        rows = repo.top_urls(
            tenant_id=tenant_id,
            limit=limit,
            occurred_from=occurred_from_utc,
            occurred_to=occurred_to_utc,
            event_type=event_type,
            source=source,
            severity=severity,
            geo_country=geo_country,
            is_bot=is_bot,
        )
        items = [{"key": key, "value": value} for key, value in rows]
        return {"items": items, "data_source": "direct_query"}

    def unique_users(
        self,
        session: Session,
        tenant_id: uuid.UUID,
        occurred_from: datetime | None,
        occurred_to: datetime | None,
        event_type: str | None,
        source: str | None,
        severity: str | None,
        geo_country: str | None,
        is_bot: bool | None,
    ) -> dict[str, object]:
        occurred_from_utc, occurred_to_utc = _normalize_window(occurred_from, occurred_to)

        repo = EventRawRepository(session)
        value = repo.unique_users(
            tenant_id=tenant_id,
            occurred_from=occurred_from_utc,
            occurred_to=occurred_to_utc,
            event_type=event_type,
            source=source,
            severity=severity,
            geo_country=geo_country,
            is_bot=is_bot,
        )
        return {"value": value, "data_source": "direct_query"}

