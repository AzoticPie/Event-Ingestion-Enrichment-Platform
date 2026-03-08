"""Repository for aggregate rollup materialization and reads."""

from __future__ import annotations

import hashlib
import uuid
from datetime import datetime

from sqlalchemy import asc, delete, desc, func, select
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.orm import Session

from event_platform.infrastructure.db.models import (
    AggregateRollup,
    AggregateRollupCoverageSegment,
    EventEnriched,
    EventNormalized,
)

ROLLUP_METRIC_EVENTS_COUNT = "events.count"
ROLLUP_METRIC_EVENTS_BY_TYPE = "events.by_type"
ROLLUP_METRIC_EVENTS_BY_URL_HOST = "events.by_url_host"
ROLLUP_DIMENSION_ALL = "__all__"
ROLLUP_GRANULARITY_MINUTE = "minute"
ROLLUP_METRIC_GROUP_CORE_DASHBOARD = "core_dashboard"


def _advisory_lock_key(tenant_id: uuid.UUID, metric_group: str, bucket_granularity: str) -> int:
    raw = f"{tenant_id}:{metric_group}:{bucket_granularity}".encode("utf-8")
    value = int.from_bytes(hashlib.sha256(raw).digest()[:8], byteorder="big", signed=False)
    if value >= 2**63:
        value -= 2**64
    return value


class RollupRepository:
    """Data access for rollup build/read workflows."""

    def __init__(self, session: Session) -> None:
        self._session = session

    def try_acquire_rollup_lock(
        self,
        tenant_id: uuid.UUID,
        metric_group: str = ROLLUP_METRIC_GROUP_CORE_DASHBOARD,
        bucket_granularity: str = ROLLUP_GRANULARITY_MINUTE,
    ) -> bool:
        key = _advisory_lock_key(tenant_id, metric_group, bucket_granularity)
        acquired = self._session.execute(select(func.pg_try_advisory_xact_lock(key))).scalar_one()
        return bool(acquired)

    def delete_rollup_window(
        self,
        tenant_id: uuid.UUID,
        window_start: datetime,
        window_end: datetime,
        bucket_granularity: str = ROLLUP_GRANULARITY_MINUTE,
    ) -> int:
        stmt = delete(AggregateRollup).where(
            AggregateRollup.tenant_id == tenant_id,
            AggregateRollup.bucket_granularity == bucket_granularity,
            AggregateRollup.bucket_start >= window_start,
            AggregateRollup.bucket_start < window_end,
        )
        result = self._session.execute(stmt)
        self._session.flush()
        return int(result.rowcount or 0)

    def upsert_rollup_rows(self, rows: list[dict[str, object]]) -> int:
        if not rows:
            return 0

        stmt = insert(AggregateRollup).values(rows)
        stmt = stmt.on_conflict_do_update(
            index_elements=[
                "tenant_id",
                "bucket_start",
                "bucket_granularity",
                "metric_name",
                "dimension_key",
            ],
            set_={
                "metric_value": stmt.excluded.metric_value,
                "updated_at": func.now(),
            },
        )
        self._session.execute(stmt)
        self._session.flush()
        return len(rows)

    def rebuild_rollup_window_for_tenant(
        self,
        tenant_id: uuid.UUID,
        window_start: datetime,
        window_end: datetime,
    ) -> int:
        if window_start >= window_end:
            return 0

        self.delete_rollup_window(tenant_id=tenant_id, window_start=window_start, window_end=window_end)

        bucket_start = func.date_trunc("minute", EventNormalized.occurred_at_utc).label("bucket_start")

        count_rows = self._session.execute(
            select(bucket_start, func.count().label("value"))
            .select_from(EventNormalized)
            .where(
                EventNormalized.tenant_id == tenant_id,
                EventNormalized.occurred_at_utc >= window_start,
                EventNormalized.occurred_at_utc < window_end,
            )
            .group_by(bucket_start)
        ).all()

        type_rows = self._session.execute(
            select(bucket_start, EventNormalized.event_type_canonical, func.count().label("value"))
            .select_from(EventNormalized)
            .where(
                EventNormalized.tenant_id == tenant_id,
                EventNormalized.occurred_at_utc >= window_start,
                EventNormalized.occurred_at_utc < window_end,
            )
            .group_by(bucket_start, EventNormalized.event_type_canonical)
        ).all()

        host_rows = self._session.execute(
            select(bucket_start, EventEnriched.url_host, func.count().label("value"))
            .select_from(EventNormalized)
            .join(EventEnriched, EventEnriched.event_id == EventNormalized.event_id)
            .where(
                EventNormalized.tenant_id == tenant_id,
                EventNormalized.occurred_at_utc >= window_start,
                EventNormalized.occurred_at_utc < window_end,
                EventEnriched.url_host.is_not(None),
                func.length(func.btrim(EventEnriched.url_host)) > 0,
            )
            .group_by(bucket_start, EventEnriched.url_host)
        ).all()

        rows: list[dict[str, object]] = []

        for bucket, value in count_rows:
            rows.append(
                {
                    "tenant_id": tenant_id,
                    "bucket_start": bucket,
                    "bucket_granularity": ROLLUP_GRANULARITY_MINUTE,
                    "metric_name": ROLLUP_METRIC_EVENTS_COUNT,
                    "dimension_key": ROLLUP_DIMENSION_ALL,
                    "metric_value": int(value),
                }
            )

        for bucket, event_type, value in type_rows:
            rows.append(
                {
                    "tenant_id": tenant_id,
                    "bucket_start": bucket,
                    "bucket_granularity": ROLLUP_GRANULARITY_MINUTE,
                    "metric_name": ROLLUP_METRIC_EVENTS_BY_TYPE,
                    "dimension_key": str(event_type),
                    "metric_value": int(value),
                }
            )

        for bucket, host, value in host_rows:
            normalized_host = str(host).strip()
            if not normalized_host:
                continue
            rows.append(
                {
                    "tenant_id": tenant_id,
                    "bucket_start": bucket,
                    "bucket_granularity": ROLLUP_GRANULARITY_MINUTE,
                    "metric_name": ROLLUP_METRIC_EVENTS_BY_URL_HOST,
                    "dimension_key": normalized_host,
                    "metric_value": int(value),
                }
            )

        return self.upsert_rollup_rows(rows)

    def get_rollup_count(
        self,
        tenant_id: uuid.UUID,
        window_start: datetime,
        window_end: datetime,
    ) -> int:
        value = self._session.execute(
            select(func.coalesce(func.sum(AggregateRollup.metric_value), 0))
            .where(
                AggregateRollup.tenant_id == tenant_id,
                AggregateRollup.bucket_granularity == ROLLUP_GRANULARITY_MINUTE,
                AggregateRollup.metric_name == ROLLUP_METRIC_EVENTS_COUNT,
                AggregateRollup.dimension_key == ROLLUP_DIMENSION_ALL,
                AggregateRollup.bucket_start >= window_start,
                AggregateRollup.bucket_start < window_end,
            )
        ).scalar_one()
        return int(value)

    def get_rollup_top_dimensions(
        self,
        tenant_id: uuid.UUID,
        metric_name: str,
        window_start: datetime,
        window_end: datetime,
        limit: int,
    ) -> list[tuple[str, int]]:
        rows = self._session.execute(
            select(AggregateRollup.dimension_key, func.sum(AggregateRollup.metric_value).label("value"))
            .where(
                AggregateRollup.tenant_id == tenant_id,
                AggregateRollup.bucket_granularity == ROLLUP_GRANULARITY_MINUTE,
                AggregateRollup.metric_name == metric_name,
                AggregateRollup.bucket_start >= window_start,
                AggregateRollup.bucket_start < window_end,
            )
            .group_by(AggregateRollup.dimension_key)
            .order_by(desc("value"), asc(AggregateRollup.dimension_key))
            .limit(limit)
        ).all()
        return [(str(dimension_key), int(value)) for dimension_key, value in rows]

    def list_coverage_segments(
        self,
        tenant_id: uuid.UUID,
        bucket_granularity: str = ROLLUP_GRANULARITY_MINUTE,
        metric_group: str = ROLLUP_METRIC_GROUP_CORE_DASHBOARD,
    ) -> list[AggregateRollupCoverageSegment]:
        rows = self._session.execute(
            select(AggregateRollupCoverageSegment)
            .where(
                AggregateRollupCoverageSegment.tenant_id == tenant_id,
                AggregateRollupCoverageSegment.bucket_granularity == bucket_granularity,
                AggregateRollupCoverageSegment.metric_group == metric_group,
            )
            .order_by(AggregateRollupCoverageSegment.segment_start.asc())
        ).scalars()
        return list(rows)

    def merge_coverage_segment(
        self,
        tenant_id: uuid.UUID,
        segment_start: datetime,
        segment_end: datetime,
        bucket_granularity: str = ROLLUP_GRANULARITY_MINUTE,
        metric_group: str = ROLLUP_METRIC_GROUP_CORE_DASHBOARD,
    ) -> None:
        if segment_start >= segment_end:
            return

        overlapping = self._session.execute(
            select(AggregateRollupCoverageSegment)
            .where(
                AggregateRollupCoverageSegment.tenant_id == tenant_id,
                AggregateRollupCoverageSegment.bucket_granularity == bucket_granularity,
                AggregateRollupCoverageSegment.metric_group == metric_group,
                AggregateRollupCoverageSegment.segment_end >= segment_start,
                AggregateRollupCoverageSegment.segment_start <= segment_end,
            )
            .order_by(AggregateRollupCoverageSegment.segment_start.asc())
        ).scalars().all()

        merged_start = segment_start
        merged_end = segment_end
        overlap_ids: list[uuid.UUID] = []
        for segment in overlapping:
            merged_start = min(merged_start, segment.segment_start)
            merged_end = max(merged_end, segment.segment_end)
            overlap_ids.append(segment.id)

        if overlap_ids:
            self._session.execute(delete(AggregateRollupCoverageSegment).where(AggregateRollupCoverageSegment.id.in_(overlap_ids)))

        self._session.add(
            AggregateRollupCoverageSegment(
                tenant_id=tenant_id,
                bucket_granularity=bucket_granularity,
                metric_group=metric_group,
                segment_start=merged_start,
                segment_end=merged_end,
            )
        )
        self._session.flush()

    def is_window_fully_covered(
        self,
        tenant_id: uuid.UUID,
        window_start: datetime,
        window_end: datetime,
        bucket_granularity: str = ROLLUP_GRANULARITY_MINUTE,
        metric_group: str = ROLLUP_METRIC_GROUP_CORE_DASHBOARD,
    ) -> bool:
        if window_start >= window_end:
            return False

        segments = self._session.execute(
            select(AggregateRollupCoverageSegment.segment_start, AggregateRollupCoverageSegment.segment_end)
            .where(
                AggregateRollupCoverageSegment.tenant_id == tenant_id,
                AggregateRollupCoverageSegment.bucket_granularity == bucket_granularity,
                AggregateRollupCoverageSegment.metric_group == metric_group,
                AggregateRollupCoverageSegment.segment_end > window_start,
                AggregateRollupCoverageSegment.segment_start < window_end,
            )
            .order_by(AggregateRollupCoverageSegment.segment_start.asc())
        ).all()

        cursor = window_start
        for segment_start, segment_end in segments:
            if segment_start > cursor:
                return False
            if segment_end > cursor:
                cursor = segment_end
            if cursor >= window_end:
                return True

        return cursor >= window_end

