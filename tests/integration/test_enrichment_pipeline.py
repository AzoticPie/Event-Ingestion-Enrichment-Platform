from __future__ import annotations

import uuid
from datetime import UTC, datetime

import pytest
from sqlalchemy import text

from event_platform.core.security import ingestion_key_hash, ingestion_key_prefix
from event_platform.infrastructure.db.session import session_scope
from event_platform.worker.tasks.enrichment import enrich_event


def _db_available() -> bool:
    try:
        with session_scope() as session:
            session.execute(text("SELECT 1"))
        return True
    except Exception:
        return False


@pytest.mark.integration
def test_enrichment_task_creates_projection() -> None:
    if not _db_available():
        pytest.skip("PostgreSQL unavailable for enrichment integration test")

    from fastapi.testclient import TestClient

    from event_platform.main import app

    tenant_name = f"enrichment-test-{uuid.uuid4().hex[:8]}"
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
    payload = {
        "event_type": "page_view",
        "occurred_at": datetime.now(UTC).isoformat(),
        "source": "tests",
        "url": "https://example.com/path?x=1",
        "referrer": "https://ref.example.net/a",
        "attributes": {"path": "/home"},
    }
    ingest_resp = client.post("/v1/ingest/events", json=payload, headers={"X-Ingest-Key": raw_key})
    assert ingest_resp.status_code == 202
    event_id = ingest_resp.json()["result"]["event_id"]

    enrich_event(event_id)

    with session_scope() as session:
        row = session.execute(
            text(
                "SELECT er.ingest_status, ee.event_id, ee.url_host "
                "FROM event_raw er LEFT JOIN event_enriched ee ON ee.event_id = er.id "
                "WHERE er.id = :event_id"
            ),
            {"event_id": event_id},
        ).one()

    assert row[0] == "enriched"
    assert row[1] is not None

