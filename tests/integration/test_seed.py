from __future__ import annotations

import pytest
from sqlalchemy import text

from event_platform.infrastructure.db.seed import seed
from event_platform.infrastructure.db.session import session_scope


@pytest.mark.integration
def test_seed_inserts_tenant_and_key() -> None:
    try:
        seed()
    except Exception as exc:  # pragma: no cover
        pytest.skip(f"Seed test skipped because database is unavailable: {exc}")

    with session_scope() as session:
        tenant_count = session.execute(
            text("SELECT count(*) FROM tenant WHERE name = 'demo-workspace'")
        ).scalar_one()
        key_count = session.execute(
            text(
                "SELECT count(*) FROM ingestion_key k "
                "JOIN tenant t ON t.id = k.tenant_id "
                "WHERE t.name = 'demo-workspace'"
            )
        ).scalar_one()

        assert tenant_count >= 1
        assert key_count >= 1

