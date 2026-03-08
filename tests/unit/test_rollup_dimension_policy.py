from __future__ import annotations

from event_platform.infrastructure.repositories.rollups_repo import ROLLUP_DIMENSION_ALL


def test_rollup_count_dimension_uses_sentinel() -> None:
    assert ROLLUP_DIMENSION_ALL == "__all__"

