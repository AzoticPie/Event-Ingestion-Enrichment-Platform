from __future__ import annotations

import uuid
from datetime import UTC, datetime, timedelta

import pytest
from sqlalchemy import text

from event_platform.core.security import ingestion_key_hash, ingestion_key_prefix
from event_platform.infrastructure.db.session import session_scope


def _db_available() -> bool:
    try:
        with session_scope() as session:
            session.execute(text("SELECT 1"))
        return True
    except Exception:
        return False


@pytest.mark.integration
def test_events_list_cursor_and_detail() -> None:
    if not _db_available():
        pytest.skip("PostgreSQL unavailable for query integration test")

    from fastapi.testclient import TestClient

    from event_platform.main import app

    tenant_name = f"query-test-{uuid.uuid4().hex[:8]}"
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
    for idx in range(3):
        payload = {
            "event_type": "page_view",
            "occurred_at": (now + timedelta(seconds=idx)).isoformat(),
            "source": "tests",
            "user_id": f"u{idx}",
            "attributes": {"idx": idx},
        }
        response = client.post("/v1/ingest/events", json=payload, headers={"X-Ingest-Key": raw_key})
        assert response.status_code == 202

    page1 = client.get(
        "/v1/events",
        params={"limit": 2, "sort": "desc"},
        headers={"X-Ingest-Key": raw_key},
    )
    assert page1.status_code == 200
    page1_body = page1.json()
    assert page1_body["count"] == 2
    assert page1_body["has_more"] is True
    assert page1_body["next_cursor"] is not None

    page2 = client.get(
        "/v1/events",
        params={"limit": 2, "sort": "desc", "cursor": page1_body["next_cursor"]},
        headers={"X-Ingest-Key": raw_key},
    )
    assert page2.status_code == 200
    page2_body = page2.json()
    assert page2_body["count"] >= 1

    not_bot = client.get(
        "/v1/events",
        params={"limit": 10, "is_bot": "false"},
        headers={"X-Ingest-Key": raw_key},
    )
    assert not_bot.status_code == 200
    assert not_bot.json()["count"] == 3

    only_bots = client.get(
        "/v1/events",
        params={"limit": 10, "is_bot": "true"},
        headers={"X-Ingest-Key": raw_key},
    )
    assert only_bots.status_code == 200
    assert only_bots.json()["count"] == 0

    detail_id = page1_body["items"][0]["event_id"]
    detail = client.get(f"/v1/events/{detail_id}", headers={"X-Ingest-Key": raw_key})
    assert detail.status_code == 200
    assert detail.json()["item"]["event_id"] == detail_id

