from __future__ import annotations

import uuid
from datetime import UTC, datetime, timedelta

import pytest
from sqlalchemy import text

from event_platform.core.security import ingestion_key_hash, ingestion_key_prefix
from event_platform.infrastructure.db.session import session_scope
from event_platform.worker.tasks.enrichment import enrich_event
from event_platform.worker.tasks.rollups import backfill_rollups


def _db_available() -> bool:
    try:
        with session_scope() as session:
            session.execute(text("SELECT 1"))
        return True
    except Exception:
        return False


@pytest.mark.integration
def test_backfill_rollups_writes_rows() -> None:
    if not _db_available():
        pytest.skip("PostgreSQL unavailable for rollup integration test")

    from fastapi.testclient import TestClient

    from event_platform.main import app

    tenant_name = f"rollup-task-{uuid.uuid4().hex[:8]}"
    raw_key = f"ing_{uuid.uuid4().hex}{uuid.uuid4().hex}"
    key_prefix = ingestion_key_prefix(raw_key)
    key_hash = ingestion_key_hash(raw_key)

    with session_scope() as session:
        tenant_id = uuid.uuid4()
        key_id = uuid.uuid4()
        session.execute(
            text("INSERT INTO tenant (id, name, status) VALUES (:id, :name, :status)"),
            {"id": str(tenant_id), "name": tenant_name, "status": "active"},
        )
        session.execute(
            text(
                "INSERT INTO ingestion_key (id, tenant_id, key_prefix, key_hash, is_active) "
                "VALUES (:id, :tenant_id, :key_prefix, :key_hash, true)"
            ),
            {
                "id": str(key_id),
                "tenant_id": str(tenant_id),
                "key_prefix": key_prefix,
                "key_hash": key_hash,
            },
        )

    client = TestClient(app)
    now = datetime.now(UTC)
    event_ids: list[str] = []
    for idx in range(3):
        payload = {
            "event_type": "page_view",
            "occurred_at": (now + timedelta(seconds=idx)).isoformat(),
            "source": "tests",
            "user_id": f"u{idx}",
            "url": "https://example.com/path",
            "attributes": {"idx": idx},
        }
        response = client.post("/v1/ingest/events", json=payload, headers={"X-Ingest-Key": raw_key})
        assert response.status_code == 202
        event_ids.append(response.json()["result"]["event_id"])

    for event_id in event_ids:
        enrich_event(event_id)

    task_result = backfill_rollups(
        tenant_id=str(tenant_id),
        occurred_from=(now - timedelta(minutes=1)).isoformat(),
        occurred_to=(now + timedelta(minutes=1)).isoformat(),
    )
    assert task_result["status"] == "ok"

    with session_scope() as session:
        rollup_count = session.execute(
            text("SELECT COUNT(1) FROM aggregate_rollup WHERE tenant_id = :tenant_id"),
            {"tenant_id": str(tenant_id)},
        ).scalar_one()
        assert int(rollup_count) > 0

