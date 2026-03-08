from __future__ import annotations

import uuid
from datetime import UTC, datetime

import pytest
from sqlalchemy import text

from event_platform.infrastructure.db.session import session_scope
from event_platform.infrastructure.repositories.rollups_repo import RollupRepository


def _db_available() -> bool:
    try:
        with session_scope() as session:
            session.execute(text("SELECT 1"))
        return True
    except Exception:
        return False


def test_merge_coverage_segment_and_coverage_check() -> None:
    if not _db_available():
        pytest.skip("PostgreSQL unavailable for rollup coverage unit test")

    tenant_id = uuid.uuid4()
    with session_scope() as session:
        session.execute(
            text("INSERT INTO tenant (id, name, status) VALUES (:id, :name, :status)"),
            {"id": str(tenant_id), "name": f"rollup-coverage-{tenant_id.hex[:8]}", "status": "active"},
        )

    with session_scope() as session:
        repo = RollupRepository(session)
        start = datetime(2026, 3, 7, 10, 0, 0, tzinfo=UTC)
        mid = datetime(2026, 3, 7, 10, 30, 0, tzinfo=UTC)
        end = datetime(2026, 3, 7, 11, 0, 0, tzinfo=UTC)

        repo.merge_coverage_segment(tenant_id=tenant_id, segment_start=start, segment_end=mid)
        repo.merge_coverage_segment(tenant_id=tenant_id, segment_start=mid, segment_end=end)

        assert repo.is_window_fully_covered(tenant_id=tenant_id, window_start=start, window_end=end)

