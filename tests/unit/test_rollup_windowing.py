from __future__ import annotations

from datetime import UTC, datetime

from event_platform.application.rollup_service import RollupBuildService, RollupValidationError
from event_platform.core.config import Settings


def test_split_backfill_chunks_honors_chunk_and_cap() -> None:
    settings = Settings(
        aggregate_rollup_backfill_chunk_minutes=60,
        aggregate_rollup_backfill_max_chunks_per_task=2,
    )
    service = RollupBuildService(settings=settings)

    start = datetime(2026, 3, 7, 10, 0, 0, tzinfo=UTC)
    end = datetime(2026, 3, 7, 14, 0, 0, tzinfo=UTC)
    chunks = service.split_backfill_chunks(occurred_from=start, occurred_to=end)

    assert len(chunks) == 2
    assert chunks[0][0] == start
    assert chunks[0][1].hour == 11
    assert chunks[1][0].hour == 11
    assert chunks[1][1].hour == 12


def test_split_backfill_chunks_invalid_window_raises() -> None:
    service = RollupBuildService(settings=Settings())
    at = datetime(2026, 3, 7, 10, 0, 0, tzinfo=UTC)
    try:
        service.split_backfill_chunks(occurred_from=at, occurred_to=at)
    except RollupValidationError:
        return
    assert False, "expected RollupValidationError"

