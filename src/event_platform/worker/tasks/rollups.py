"""Celery tasks for rollup refresh and backfill workflows."""

from __future__ import annotations

import uuid
from datetime import UTC, datetime, timedelta

import structlog

from event_platform.application.rollup_service import (
    RollupBuildService,
    RollupLockConflictError,
    RollupValidationError,
)
from event_platform.core.config import get_settings
from event_platform.infrastructure.db.session import session_scope
from event_platform.infrastructure.repositories.tenants_repo import TenantRepository
from event_platform.worker.celery_app import celery_app

logger = structlog.get_logger(__name__)
settings = get_settings()


def _compute_rotating_offset(
    total_active: int,
    batch_size: int,
    refresh_interval_seconds: int,
    now_utc: datetime | None = None,
) -> int:
    """Compute deterministic rotating offset so all tenants get periodic refresh."""
    if total_active <= 0:
        return 0
    effective_batch = max(1, batch_size)
    effective_interval = max(1, refresh_interval_seconds)
    timestamp = int((now_utc or datetime.now(UTC)).timestamp())
    slot = timestamp // effective_interval
    return int((slot * effective_batch) % total_active)


@celery_app.task(
    name="event_platform.refresh_recent_rollups_for_tenant",
    bind=True,
    max_retries=settings.aggregate_rollup_lock_retry_max_attempts,
    retry_backoff=settings.aggregate_rollup_lock_retry_base_seconds,
    retry_backoff_max=300,
    retry_jitter=True,
    acks_late=True,
)
def refresh_recent_rollups_for_tenant(self, tenant_id: str) -> dict[str, object]:
    """Refresh recent rollup window for one tenant with lock-based retry."""
    if not settings.aggregate_rollup_enabled:
        logger.info(
            "rollup_refresh_skipped_disabled",
            tenant_id=tenant_id,
            task_id=self.request.id,
        )
        return {"tenant_id": tenant_id, "status": "disabled"}

    tenant_uuid = uuid.UUID(tenant_id)
    now_utc = datetime.now(UTC)
    lookback = max(1, settings.aggregate_rollup_refresh_lookback_minutes)
    window_start = now_utc - timedelta(minutes=lookback)
    window_end = now_utc

    logger.info(
        "rollup_refresh_started",
        tenant_id=tenant_id,
        task_id=self.request.id,
        window_start=window_start.isoformat(),
        window_end=window_end.isoformat(),
        bucket_granularity="minute",
    )

    started = datetime.now(UTC)
    try:
        with session_scope() as session:
            result = RollupBuildService(settings).rebuild_window(
                session=session,
                tenant_id=tenant_uuid,
                window_start=window_start,
                window_end=window_end,
            )
    except RollupLockConflictError as exc:
        logger.warning(
            "rollup_lock_conflict",
            tenant_id=tenant_id,
            task_id=self.request.id,
            error=str(exc),
        )
        raise self.retry(exc=exc)
    except RollupValidationError:
        logger.exception("rollup_refresh_failed", tenant_id=tenant_id, task_id=self.request.id)
        return {"tenant_id": tenant_id, "status": "failed_validation"}
    except Exception:
        logger.exception("rollup_refresh_failed", tenant_id=tenant_id, task_id=self.request.id)
        raise

    duration_ms = int((datetime.now(UTC) - started).total_seconds() * 1000)
    logger.info(
        "rollup_refresh_completed",
        tenant_id=tenant_id,
        task_id=self.request.id,
        window_start=result.window_start.isoformat(),
        window_end=result.window_end.isoformat(),
        bucket_granularity="minute",
        rows_written=result.rows_written,
        duration_ms=duration_ms,
    )
    return {
        "tenant_id": tenant_id,
        "status": "ok",
        "rows_written": result.rows_written,
        "window_start": result.window_start.isoformat(),
        "window_end": result.window_end.isoformat(),
    }


@celery_app.task(
    name="event_platform.refresh_recent_rollups",
    bind=True,
    max_retries=0,
    acks_late=True,
)
def refresh_recent_rollups(self) -> dict[str, int]:
    """Dispatch bounded tenant refresh tasks for recent rollup windows."""
    del self

    if not settings.aggregate_rollup_enabled:
        logger.info("rollup_dispatch_skipped_disabled")
        return {"dispatched": 0}

    dispatched = 0
    batch_size = max(1, settings.aggregate_rollup_refresh_tenants_per_tick)
    inflight_cap = max(1, settings.aggregate_rollup_refresh_max_inflight_tenant_tasks)

    with session_scope() as session:
        tenant_repo = TenantRepository(session)
        total_active = tenant_repo.count_active_tenants()
        if total_active <= 0:
            logger.info("rollup_refresh_dispatched", dispatched=0, batch_size=batch_size, total_active=0, offset=0)
            return {"dispatched": 0}

        offset = _compute_rotating_offset(
            total_active=total_active,
            batch_size=batch_size,
            refresh_interval_seconds=settings.aggregate_rollup_refresh_interval_seconds,
        )
        target = min(batch_size, total_active, inflight_cap)
        tenant_ids = tenant_repo.list_active_tenant_ids(limit=target, offset=offset)
        if len(tenant_ids) < target and offset > 0:
            remainder = target - len(tenant_ids)
            tenant_ids.extend(tenant_repo.list_active_tenant_ids(limit=remainder, offset=0))

    for tenant_id in tenant_ids:
        refresh_recent_rollups_for_tenant.apply_async(
            args=[str(tenant_id)],
            queue=settings.celery_rollup_queue,
        )
        dispatched += 1

    logger.info(
        "rollup_refresh_dispatched",
        dispatched=dispatched,
        batch_size=batch_size,
        total_active=total_active,
        offset=offset,
    )
    return {"dispatched": dispatched}


@celery_app.task(
    name="event_platform.backfill_rollups",
    bind=True,
    max_retries=settings.aggregate_rollup_lock_retry_max_attempts,
    retry_backoff=settings.aggregate_rollup_lock_retry_base_seconds,
    retry_backoff_max=300,
    retry_jitter=True,
    acks_late=True,
)
def backfill_rollups(self, tenant_id: str, occurred_from: str, occurred_to: str) -> dict[str, object]:
    """Backfill rollups for bounded historical windows."""
    tenant_uuid = uuid.UUID(tenant_id)
    from_dt = datetime.fromisoformat(occurred_from)
    to_dt = datetime.fromisoformat(occurred_to)

    service = RollupBuildService(settings)
    chunks = service.split_backfill_chunks(occurred_from=from_dt, occurred_to=to_dt)
    rows_written_total = 0
    chunks_processed = 0
    continuation_enqueued = False

    for chunk_start, chunk_end in chunks:
        started = datetime.now(UTC)
        try:
            with session_scope() as session:
                result = service.rebuild_window(
                    session=session,
                    tenant_id=tenant_uuid,
                    window_start=chunk_start,
                    window_end=chunk_end,
                )
        except RollupLockConflictError as exc:
            logger.warning(
                "rollup_lock_conflict",
                tenant_id=tenant_id,
                task_id=self.request.id,
                window_start=chunk_start.isoformat(),
                window_end=chunk_end.isoformat(),
                error=str(exc),
            )
            raise self.retry(exc=exc)

        duration_ms = int((datetime.now(UTC) - started).total_seconds() * 1000)
        rows_written_total += result.rows_written
        chunks_processed += 1
        logger.info(
            "rollup_backfill_chunk_completed",
            tenant_id=tenant_id,
            task_id=self.request.id,
            window_start=result.window_start.isoformat(),
            window_end=result.window_end.isoformat(),
            bucket_granularity="minute",
            rows_written=result.rows_written,
            duration_ms=duration_ms,
            chunk_index=chunks_processed,
        )

    next_from: str | None = None
    if chunks:
        last_chunk_end = chunks[-1][1]
        if last_chunk_end < to_dt:
            next_from = last_chunk_end.isoformat()
            backfill_rollups.apply_async(
                args=[tenant_id, next_from, occurred_to],
                queue=settings.celery_rollup_queue,
            )
            continuation_enqueued = True

    return {
        "tenant_id": tenant_id,
        "status": "ok",
        "chunks_processed": chunks_processed,
        "rows_written": rows_written_total,
        "continuation_enqueued": continuation_enqueued,
        "next_from": next_from,
    }

