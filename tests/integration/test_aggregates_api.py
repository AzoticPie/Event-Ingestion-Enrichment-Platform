from __future__ import annotations

import uuid
from datetime import UTC, datetime, timedelta

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
def test_aggregate_endpoints() -> None:
    if not _db_available():
        pytest.skip("PostgreSQL unavailable for aggregate integration test")

    from fastapi.testclient import TestClient

    from event_platform.main import app

    tenant_name = f"agg-test-{uuid.uuid4().hex[:8]}"
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
    for idx in range(4):
        payload = {
            "event_type": "page_view" if idx < 3 else "checkout_completed",
            "occurred_at": (now + timedelta(seconds=idx)).isoformat(),
            "source": "tests",
            "user_id": f"u{idx % 2}",
            "url": "https://example.com/path",
            "attributes": {"idx": idx},
        }
        response = client.post("/v1/ingest/events", json=payload, headers={"X-Ingest-Key": raw_key})
        assert response.status_code == 202
        event_ids.append(response.json()["result"]["event_id"])

    for event_id in event_ids:
        enrich_event(event_id)

    window_from = (now - timedelta(minutes=5)).isoformat()
    window_to = (now + timedelta(minutes=5)).isoformat()

    count_resp = client.get(
        "/v1/aggregates/count",
        params={"occurred_from": window_from, "occurred_to": window_to},
        headers={"X-Ingest-Key": raw_key},
    )
    assert count_resp.status_code == 200
    assert count_resp.json()["value"] >= 4

    top_types = client.get(
        "/v1/aggregates/top-event-types",
        params={"occurred_from": window_from, "occurred_to": window_to, "limit": 5},
        headers={"X-Ingest-Key": raw_key},
    )
    assert top_types.status_code == 200
    assert len(top_types.json()["items"]) >= 1

    top_urls = client.get(
        "/v1/aggregates/top-urls",
        params={"occurred_from": window_from, "occurred_to": window_to, "limit": 5},
        headers={"X-Ingest-Key": raw_key},
    )
    assert top_urls.status_code == 200

    unique_users = client.get(
        "/v1/aggregates/unique-users",
        params={"occurred_from": window_from, "occurred_to": window_to},
        headers={"X-Ingest-Key": raw_key},
    )
    assert unique_users.status_code == 200
    assert unique_users.json()["value"] >= 1

    invalid_window_count = client.get(
        "/v1/aggregates/count",
        params={"occurred_from": window_to, "occurred_to": window_from},
        headers={"X-Ingest-Key": raw_key},
    )
    assert invalid_window_count.status_code == 422

    invalid_window_top_types = client.get(
        "/v1/aggregates/top-event-types",
        params={"occurred_from": window_to, "occurred_to": window_from, "limit": 5},
        headers={"X-Ingest-Key": raw_key},
    )
    assert invalid_window_top_types.status_code == 422

    invalid_window_top_urls = client.get(
        "/v1/aggregates/top-urls",
        params={"occurred_from": window_to, "occurred_to": window_from, "limit": 5},
        headers={"X-Ingest-Key": raw_key},
    )
    assert invalid_window_top_urls.status_code == 422

    invalid_window_unique_users = client.get(
        "/v1/aggregates/unique-users",
        params={"occurred_from": window_to, "occurred_to": window_from},
        headers={"X-Ingest-Key": raw_key},
    )
    assert invalid_window_unique_users.status_code == 422

