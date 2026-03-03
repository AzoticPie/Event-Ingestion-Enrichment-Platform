from __future__ import annotations

from datetime import UTC, date, datetime

import pytest
from sqlalchemy import text

from event_platform.infrastructure.db.session import session_scope
from event_platform.infrastructure.repositories.events_repo import EventNormalizedRepository, EventRawRepository
from event_platform.infrastructure.repositories.keys_repo import IngestionKeyRepository
from event_platform.infrastructure.repositories.tenants_repo import TenantRepository


@pytest.mark.integration
def test_repository_create_and_lookup_paths() -> None:
    try:
        with session_scope() as session:
            session.execute(text("SELECT 1"))
    except Exception as exc:  # pragma: no cover
        pytest.skip(f"PostgreSQL unavailable for integration test: {exc}")

    with session_scope() as session:
        tenant_repo = TenantRepository(session)
        key_repo = IngestionKeyRepository(session)
        raw_repo = EventRawRepository(session)
        normalized_repo = EventNormalizedRepository(session)

        tenant = tenant_repo.get_by_name("repo-test-tenant")
        if tenant is None:
            tenant = tenant_repo.create(name="repo-test-tenant")

        key = key_repo.find_active_by_prefix("repotest")
        if key is None:
            key = key_repo.create(
                tenant_id=tenant.id,
                key_prefix="repotest",
                key_hash="sha256-repotest",
            )

        assert key_repo.find_active_by_prefix("repotest") is not None

        raw_event = raw_repo.create(
            tenant_id=tenant.id,
            source="tests",
            event_type_original="page_view",
            occurred_at_original=datetime.now(UTC),
            payload_jsonb={"a": 1},
            headers_jsonb={"x-request-id": "abc"},
            dedupe_hash="dedupe-hash-repotest",
            idempotency_key="idem-repotest",
        )
        assert raw_repo.find_by_idempotency_key(tenant.id, "idem-repotest") is not None
        assert raw_repo.find_by_dedupe_hash(tenant.id, "dedupe-hash-repotest") is not None

        normalized_repo.create(
            event_id=raw_event.id,
            tenant_id=tenant.id,
            event_type_canonical="page_view",
            occurred_at_utc=datetime.now(UTC),
            source="tests",
            ingestion_date=date.today(),
        )
        assert normalized_repo.get_by_event_id(raw_event.id) is not None

