"""Application services for aggregate rollup build and read flows."""

from __future__ import annotations

import uuid
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta

from sqlalchemy.orm import Session

from event_platform.core.config import Settings, get_settings
from event_platform.infrastructure.repositories.rollups_repo import (
    ROLLUP_GRANULARITY_MINUTE,
    ROLLUP_METRIC_GROUP_CORE_DASHBOARD,
    RollupRepository,
)


class RollupValidationError(ValueError):
    """Raised when rollup window inputs are invalid."""


class RollupLockConflictError(RuntimeError):
    """Raised when rollup lock cannot be acquired for a tenant scope."""


@dataclass(slots=True)
class RollupBuildResult:
    """Result envelope for one rollup materialization run."""

    tenant_id: uuid.UUID
    window_start: datetime
    window_end: datetime
    rows_written: int


def _to_utc(value: datetime) -> datetime:
    if value.tzinfo is None:
        return value.replace(tzinfo=UTC)
    return value.astimezone(UTC)


def _floor_minute(value: datetime) -> datetime:
    return value.replace(second=0, microsecond=0)


def _ceil_minute(value: datetime) -> datetime:
    floored = _floor_minute(value)
    if value == floored:
        return floored
    return floored + timedelta(minutes=1)


def _is_minute_start(value: datetime) -> bool:
    return value.second == 0 and value.microsecond == 0


def _is_minute_end_inclusive(value: datetime) -> bool:
    return value.second == 59 and value.microsecond == 999999


class RollupBuildService:
    """Build minute-granularity rollups with coverage tracking."""

    def __init__(self, settings: Settings | None = None) -> None:
        self._settings = settings or get_settings()

    def rebuild_window(
        self,
        session: Session,
        tenant_id: uuid.UUID,
        window_start: datetime,
        window_end: datetime,
        metric_group: str = ROLLUP_METRIC_GROUP_CORE_DASHBOARD,
        bucket_granularity: str = ROLLUP_GRANULARITY_MINUTE,
    ) -> RollupBuildResult:
        start_utc = _floor_minute(_to_utc(window_start))
        end_utc = _ceil_minute(_to_utc(window_end))
        if start_utc >= end_utc:
            raise RollupValidationError("window_start must be < window_end")

        repo = RollupRepository(session)
        acquired = repo.try_acquire_rollup_lock(
            tenant_id=tenant_id,
            metric_group=metric_group,
            bucket_granularity=bucket_granularity,
        )
        if not acquired:
            raise RollupLockConflictError("rollup lock unavailable")

        rows_written = repo.rebuild_rollup_window_for_tenant(
            tenant_id=tenant_id,
            window_start=start_utc,
            window_end=end_utc,
        )
        repo.merge_coverage_segment(
            tenant_id=tenant_id,
            segment_start=start_utc,
            segment_end=end_utc,
            metric_group=metric_group,
            bucket_granularity=bucket_granularity,
        )

        return RollupBuildResult(
            tenant_id=tenant_id,
            window_start=start_utc,
            window_end=end_utc,
            rows_written=rows_written,
        )

    def split_backfill_chunks(
        self,
        occurred_from: datetime,
        occurred_to: datetime,
    ) -> list[tuple[datetime, datetime]]:
        start_utc = _floor_minute(_to_utc(occurred_from))
        end_utc = _ceil_minute(_to_utc(occurred_to))
        if start_utc >= end_utc:
            raise RollupValidationError("occurred_from must be < occurred_to")

        chunk_minutes = max(1, self._settings.aggregate_rollup_backfill_chunk_minutes)
        max_chunks = max(1, self._settings.aggregate_rollup_backfill_max_chunks_per_task)

        chunks: list[tuple[datetime, datetime]] = []
        cursor = start_utc
        while cursor < end_utc and len(chunks) < max_chunks:
            next_cursor = min(cursor + timedelta(minutes=chunk_minutes), end_utc)
            chunks.append((cursor, next_cursor))
            cursor = next_cursor

        return chunks


class RollupReadService:
    """Read helper for safe rollup eligibility and retrieval windows."""

    def __init__(self, settings: Settings | None = None) -> None:
        self._settings = settings or get_settings()

    def to_rollup_window_or_none(
        self,
        occurred_from: datetime | None,
        occurred_to: datetime | None,
    ) -> tuple[datetime, datetime] | None:
        if occurred_from is None or occurred_to is None:
            return None

        from_utc = _to_utc(occurred_from)
        to_utc = _to_utc(occurred_to)
        if from_utc >= to_utc:
            return None

        if not _is_minute_start(from_utc) or not _is_minute_end_inclusive(to_utc):
            return None

        end_exclusive = to_utc + timedelta(microseconds=1)
        window_minutes = (end_exclusive - from_utc).total_seconds() / 60
        if window_minutes <= 0:
            return None
        if window_minutes > float(self._settings.aggregate_rollup_max_window_minutes):
            return None

        return from_utc, end_exclusive

