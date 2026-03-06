from __future__ import annotations

import uuid
from datetime import UTC, datetime

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
def test_single_ingestion_and_event_list_flow() -> None:
    if not _db_available():
        pytest.skip("PostgreSQL unavailable for ingestion integration test")

    from fastapi.testclient import TestClient

    from event_platform.main import app

    tenant_name = f"ingestion-test-{uuid.uuid4().hex[:8]}"
    raw_key = f"ing_{uuid.uuid4().hex}{uuid.uuid4().hex}"
    key_prefix = ingestion_key_prefix(raw_key)
    key_hash = ingestion_key_hash(raw_key)

    with session_scope() as session:
        tenant_id = uuid.uuid4()
        key_id = uuid.uuid4()
        session.execute(
            text(
                "INSERT INTO tenant (id, name, status) VALUES (:id, :name, :status)"
            ),
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
        "user_id": "u-1",
        "session_id": "s-1",
        "attributes": {"path": "/home"},
    }

    ingest_resp = client.post("/v1/ingest/events", json=payload, headers={"X-Ingest-Key": raw_key})
    assert ingest_resp.status_code == 202
    assert ingest_resp.json()["result"]["status"] == "accepted"

    event_id = ingest_resp.json()["result"]["event_id"]
    with session_scope() as session:
        headers_jsonb = session.execute(
            text("SELECT headers_jsonb FROM event_raw WHERE id = :event_id"),
            {"event_id": event_id},
        ).scalar_one()

    assert "x-ingest-key" not in headers_jsonb

    list_resp = client.get("/v1/events", headers={"X-Ingest-Key": raw_key})
    assert list_resp.status_code == 200
    data = list_resp.json()
    assert data["count"] >= 1
    assert any(item["event_type"] == "page_view" for item in data["items"])

    canonicalized_filter_resp = client.get(
        "/v1/events",
        params={"event_type": "Page View"},
        headers={"X-Ingest-Key": raw_key},
    )
    assert canonicalized_filter_resp.status_code == 200
    filtered_data = canonicalized_filter_resp.json()
    assert filtered_data["count"] >= 1
    assert all(item["event_type"] == "page_view" for item in filtered_data["items"])


@pytest.mark.integration
def test_idempotency_duplicate_flow() -> None:
    if not _db_available():
        pytest.skip("PostgreSQL unavailable for idempotency integration test")

    from fastapi.testclient import TestClient

    from event_platform.main import app

    tenant_name = f"idempotency-test-{uuid.uuid4().hex[:8]}"
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
        "event_type": "checkout_completed",
        "occurred_at": datetime.now(UTC).isoformat(),
        "source": "tests",
        "idempotency_key": "idem-replay-1",
        "attributes": {"order_id": "order-123"},
    }

    first = client.post("/v1/ingest/events", json=payload, headers={"X-Ingest-Key": raw_key})
    second = client.post("/v1/ingest/events", json=payload, headers={"X-Ingest-Key": raw_key})

    assert first.status_code == 202
    assert second.status_code == 202
    assert first.json()["result"]["event_id"] == second.json()["result"]["event_id"]
    assert second.json()["result"]["status"] == "duplicate"
    assert second.json()["result"]["duplicate_reason"] == "idempotency_key"

    with session_scope() as session:
        headers_jsonb = session.execute(
            text("SELECT headers_jsonb FROM event_raw WHERE id = :event_id"),
            {"event_id": first.json()["result"]["event_id"]},
        ).scalar_one()

    assert "x-ingest-key" not in headers_jsonb


@pytest.mark.integration
def test_dedupe_hash_distinguishes_extended_payload_fields() -> None:
    if not _db_available():
        pytest.skip("PostgreSQL unavailable for dedupe integration test")

    from fastapi.testclient import TestClient

    from event_platform.main import app

    tenant_name = f"dedupe-test-{uuid.uuid4().hex[:8]}"
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
    occurred_at = datetime.now(UTC).isoformat()
    base_payload = {
        "event_type": "purchase_submitted",
        "occurred_at": occurred_at,
        "source": "tests",
        "attributes": {"order_id": "o-1"},
    }

    first = client.post("/v1/ingest/events", json={**base_payload, "severity": "info"}, headers={"X-Ingest-Key": raw_key})
    second = client.post(
        "/v1/ingest/events",
        json={**base_payload, "severity": "critical"},
        headers={"X-Ingest-Key": raw_key},
    )

    assert first.status_code == 202
    assert second.status_code == 202
    assert first.json()["result"]["status"] == "accepted"
    assert second.json()["result"]["status"] == "accepted"
    assert first.json()["result"]["event_id"] != second.json()["result"]["event_id"]


@pytest.mark.integration
def test_batch_ingestion_continues_when_one_publish_fails(monkeypatch: pytest.MonkeyPatch) -> None:
    if not _db_available():
        pytest.skip("PostgreSQL unavailable for batch enrichment publish integration test")

    from fastapi.testclient import TestClient

    from event_platform.api.routes import ingestion as ingestion_route
    from event_platform.main import app

    tenant_name = f"batch-publish-failure-{uuid.uuid4().hex[:8]}"
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

    publish_calls: list[str] = []

    def _fake_apply_async(*args, **kwargs):
        event_id = kwargs.get("args", [None])[0]
        publish_calls.append(event_id)
        if len(publish_calls) == 1:
            raise RuntimeError("simulated broker outage")
        return {"task_id": f"fake-{event_id}"}

    monkeypatch.setattr(ingestion_route.enrich_event, "apply_async", _fake_apply_async)

    client = TestClient(app)
    payload = {
        "events": [
            {
                "event_type": "batch_event",
                "occurred_at": datetime.now(UTC).isoformat(),
                "source": "tests",
                "session_id": "s-1",
                "attributes": {"idx": 1},
            },
            {
                "event_type": "batch_event",
                "occurred_at": datetime.now(UTC).isoformat(),
                "source": "tests",
                "session_id": "s-2",
                "attributes": {"idx": 2},
            },
        ]
    }

    response = client.post("/v1/ingest/events:batch", json=payload, headers={"X-Ingest-Key": raw_key})
    assert response.status_code == 202
    assert len(publish_calls) == 2

    results = response.json()["results"]
    first_event_id = results[0]["event_id"]
    second_event_id = results[1]["event_id"]

    with session_scope() as session:
        first_status = session.execute(
            text("SELECT ingest_status FROM event_raw WHERE id = :event_id"),
            {"event_id": first_event_id},
        ).scalar_one()
        second_status = session.execute(
            text("SELECT ingest_status FROM event_raw WHERE id = :event_id"),
            {"event_id": second_event_id},
        ).scalar_one()

    assert first_status == "failed_terminal"
    assert second_status == "queued"

