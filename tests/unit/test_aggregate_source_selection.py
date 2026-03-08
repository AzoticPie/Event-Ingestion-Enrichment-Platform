from __future__ import annotations

import uuid
from datetime import UTC, datetime

from event_platform.application.aggregate_service import AggregateService
from event_platform.core.config import Settings


def test_aggregate_source_selection_open_window_disables_rollup() -> None:
    service = AggregateService(settings=Settings(aggregate_rollup_enabled=True))
    now = datetime(2026, 3, 7, 12, 0, 0, tzinfo=UTC)
    value = service._rollup_window_or_none(now, None)
    assert value is None


def test_aggregate_source_selection_requires_minute_aligned_bounds() -> None:
    service = AggregateService(settings=Settings(aggregate_rollup_enabled=True))
    from_dt = datetime(2026, 3, 7, 12, 0, 0, tzinfo=UTC)
    to_dt = datetime(2026, 3, 7, 12, 59, 59, 999999, tzinfo=UTC)
    assert service._rollup_window_or_none(from_dt, to_dt) is not None

    not_aligned_to = datetime(2026, 3, 7, 12, 59, 59, tzinfo=UTC)
    assert service._rollup_window_or_none(from_dt, not_aligned_to) is None


def test_no_filters_helper() -> None:
    _ = uuid.uuid4()
    assert AggregateService._no_filters(None, None, None)
    assert not AggregateService._no_filters(None, "x")

