from __future__ import annotations

import uuid
from contextlib import contextmanager
from datetime import UTC, datetime
from types import SimpleNamespace

from event_platform.worker.tasks import rollups


def test_compute_rotating_offset_advances_and_wraps() -> None:
    total_active = 5
    batch_size = 2
    refresh_interval_seconds = 60

    # slot=0
    assert rollups._compute_rotating_offset(
        total_active=total_active,
        batch_size=batch_size,
        refresh_interval_seconds=refresh_interval_seconds,
        now_utc=None,
    ) >= 0

    # explicit timestamps for deterministic validation
    class _Now:
        def __init__(self, ts: int) -> None:
            self._ts = ts

        def timestamp(self) -> float:
            return float(self._ts)

    assert (
        rollups._compute_rotating_offset(
            total_active=total_active,
            batch_size=batch_size,
            refresh_interval_seconds=refresh_interval_seconds,
            now_utc=_Now(0),
        )
        == 0
    )
    assert (
        rollups._compute_rotating_offset(
            total_active=total_active,
            batch_size=batch_size,
            refresh_interval_seconds=refresh_interval_seconds,
            now_utc=_Now(60),
        )
        == 2
    )
    assert (
        rollups._compute_rotating_offset(
            total_active=total_active,
            batch_size=batch_size,
            refresh_interval_seconds=refresh_interval_seconds,
            now_utc=_Now(120),
        )
        == 4
    )
    assert (
        rollups._compute_rotating_offset(
            total_active=total_active,
            batch_size=batch_size,
            refresh_interval_seconds=refresh_interval_seconds,
            now_utc=_Now(180),
        )
        == 1
    )


def test_refresh_tasks_skip_when_rollups_disabled(monkeypatch) -> None:
    monkeypatch.setattr(rollups.settings, "aggregate_rollup_enabled", False)

    dispatch_result = rollups.refresh_recent_rollups()
    assert dispatch_result == {"dispatched": 0}

    tenant_result = rollups.refresh_recent_rollups_for_tenant("00000000-0000-0000-0000-000000000001")
    assert tenant_result["status"] == "disabled"


def test_refresh_dispatch_respects_inflight_cap(monkeypatch) -> None:
    monkeypatch.setattr(rollups.settings, "aggregate_rollup_enabled", True)
    monkeypatch.setattr(rollups.settings, "aggregate_rollup_refresh_tenants_per_tick", 50)
    monkeypatch.setattr(rollups.settings, "aggregate_rollup_refresh_max_inflight_tenant_tasks", 3)
    monkeypatch.setattr(rollups.settings, "aggregate_rollup_refresh_interval_seconds", 60)

    @contextmanager
    def _fake_session_scope():
        yield object()

    requested_limits: list[int] = []

    class _FakeTenantRepo:
        def __init__(self, _session: object) -> None:
            pass

        def count_active_tenants(self) -> int:
            return 10

        def list_active_tenant_ids(self, limit: int, offset: int = 0) -> list[uuid.UUID]:
            del offset
            requested_limits.append(limit)
            return [uuid.uuid4() for _ in range(limit)]

    dispatched_calls: list[tuple[list[str], str]] = []

    def _fake_apply_async(*, args: list[str], queue: str) -> None:
        dispatched_calls.append((args, queue))

    monkeypatch.setattr(rollups, "session_scope", _fake_session_scope)
    monkeypatch.setattr(rollups, "TenantRepository", _FakeTenantRepo)
    monkeypatch.setattr(rollups, "_compute_rotating_offset", lambda **_: 0)
    monkeypatch.setattr(rollups.refresh_recent_rollups_for_tenant, "apply_async", _fake_apply_async)

    result = rollups.refresh_recent_rollups()

    assert result == {"dispatched": 3}
    assert requested_limits == [3]
    assert len(dispatched_calls) == 3


def test_backfill_rollups_enqueues_continuation_when_range_exceeds_chunk_cap(monkeypatch) -> None:
    monkeypatch.setattr(rollups.settings, "aggregate_rollup_backfill_chunk_minutes", 60)
    monkeypatch.setattr(rollups.settings, "aggregate_rollup_backfill_max_chunks_per_task", 2)

    @contextmanager
    def _fake_session_scope():
        yield object()

    chunks = [
        (
            datetime(2026, 3, 7, 10, 0, 0, tzinfo=UTC),
            datetime(2026, 3, 7, 11, 0, 0, tzinfo=UTC),
        ),
        (
            datetime(2026, 3, 7, 11, 0, 0, tzinfo=UTC),
            datetime(2026, 3, 7, 12, 0, 0, tzinfo=UTC),
        ),
    ]

    class _FakeBuildService:
        def __init__(self, settings: object) -> None:
            del settings

        def split_backfill_chunks(self, occurred_from: datetime, occurred_to: datetime) -> list[tuple[datetime, datetime]]:
            del occurred_from, occurred_to
            return chunks

        def rebuild_window(
            self,
            session: object,
            tenant_id: uuid.UUID,
            window_start: datetime,
            window_end: datetime,
        ) -> SimpleNamespace:
            del session, tenant_id
            return SimpleNamespace(window_start=window_start, window_end=window_end, rows_written=7)

    continuation_calls: list[tuple[list[str], str]] = []

    def _fake_apply_async(*, args: list[str], queue: str) -> None:
        continuation_calls.append((args, queue))

    monkeypatch.setattr(rollups, "session_scope", _fake_session_scope)
    monkeypatch.setattr(rollups, "RollupBuildService", _FakeBuildService)
    monkeypatch.setattr(rollups.backfill_rollups, "apply_async", _fake_apply_async)

    tenant_id = str(uuid.uuid4())
    occurred_from = "2026-03-07T10:00:00+00:00"
    occurred_to = "2026-03-07T14:00:00+00:00"
    result = rollups.backfill_rollups(tenant_id=tenant_id, occurred_from=occurred_from, occurred_to=occurred_to)

    assert result["status"] == "ok"
    assert result["chunks_processed"] == 2
    assert result["rows_written"] == 14
    assert result["continuation_enqueued"] is True
    assert result["next_from"] == "2026-03-07T12:00:00+00:00"
    assert continuation_calls == [
        (
            [tenant_id, "2026-03-07T12:00:00+00:00", occurred_to],
            rollups.settings.celery_rollup_queue,
        )
    ]
