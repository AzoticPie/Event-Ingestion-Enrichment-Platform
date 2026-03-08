"""Aggregate read use-cases for dashboard-style endpoints."""

from __future__ import annotations

import uuid
from datetime import UTC, datetime

import structlog
from sqlalchemy.orm import Session

from event_platform.application.query_service import QueryValidationError
from event_platform.application.rollup_service import RollupReadService
from event_platform.core.config import Settings, get_settings
from event_platform.infrastructure.repositories.events_repo import EventRawRepository
from event_platform.infrastructure.repositories.rollups_repo import RollupRepository

logger = structlog.get_logger(__name__)


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

    def __init__(self, settings: Settings | None = None) -> None:
        self._settings = settings or get_settings()
        self._rollup_read_service = RollupReadService(self._settings)

    @staticmethod
    def _no_filters(*values: object) -> bool:
        return all(value is None for value in values)

    def _rollup_window_or_none(
        self,
        occurred_from: datetime | None,
        occurred_to: datetime | None,
    ) -> tuple[datetime, datetime] | None:
        if not self._settings.aggregate_rollup_enabled:
            return None
        return self._rollup_read_service.to_rollup_window_or_none(
            occurred_from=occurred_from,
            occurred_to=occurred_to,
        )

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

        rollup_window = self._rollup_window_or_none(occurred_from_utc, occurred_to_utc)
        if rollup_window is not None and self._no_filters(
            event_type,
            severity,
            source,
            user_id,
            session_id,
            ingest_status,
            geo_country,
            is_bot,
        ):
            window_start, window_end = rollup_window
            try:
                rollup_repo = RollupRepository(session)
                if rollup_repo.is_window_fully_covered(
                    tenant_id=tenant_id,
                    window_start=window_start,
                    window_end=window_end,
                ):
                    value = rollup_repo.get_rollup_count(
                        tenant_id=tenant_id,
                        window_start=window_start,
                        window_end=window_end,
                    )
                    return {"value": value, "data_source": "rollup"}
            except Exception:
                logger.exception("aggregate_rollup_count_fallback", tenant_id=str(tenant_id))

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

        rollup_window = self._rollup_window_or_none(occurred_from_utc, occurred_to_utc)
        if rollup_window is not None and self._no_filters(source, severity, geo_country, is_bot):
            window_start, window_end = rollup_window
            try:
                rollup_repo = RollupRepository(session)
                if rollup_repo.is_window_fully_covered(
                    tenant_id=tenant_id,
                    window_start=window_start,
                    window_end=window_end,
                ):
                    rows = rollup_repo.get_rollup_top_dimensions(
                        tenant_id=tenant_id,
                        metric_name="events.by_type",
                        window_start=window_start,
                        window_end=window_end,
                        limit=limit,
                    )
                    items = [{"key": key, "value": value} for key, value in rows]
                    return {"items": items, "data_source": "rollup"}
            except Exception:
                logger.exception("aggregate_rollup_top_types_fallback", tenant_id=str(tenant_id))

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

        rollup_window = self._rollup_window_or_none(occurred_from_utc, occurred_to_utc)
        if rollup_window is not None and self._no_filters(event_type, source, severity, geo_country, is_bot):
            window_start, window_end = rollup_window
            try:
                rollup_repo = RollupRepository(session)
                if rollup_repo.is_window_fully_covered(
                    tenant_id=tenant_id,
                    window_start=window_start,
                    window_end=window_end,
                ):
                    rows = rollup_repo.get_rollup_top_dimensions(
                        tenant_id=tenant_id,
                        metric_name="events.by_url_host",
                        window_start=window_start,
                        window_end=window_end,
                        limit=limit,
                    )
                    items = [{"key": key, "value": value} for key, value in rows]
                    return {"items": items, "data_source": "rollup"}
            except Exception:
                logger.exception("aggregate_rollup_top_urls_fallback", tenant_id=str(tenant_id))

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

