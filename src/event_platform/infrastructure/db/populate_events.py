"""Populate local database with demo events for manual frontend testing."""

from __future__ import annotations

import uuid
from datetime import UTC, datetime, timedelta

from event_platform.api.schemas.ingestion import IngestEventRequest
from event_platform.application.ingestion_service import IngestionService
from event_platform.core.security import ingestion_key_hash, ingestion_key_prefix
from event_platform.infrastructure.db.session import session_scope
from event_platform.infrastructure.repositories.keys_repo import IngestionKeyRepository
from event_platform.infrastructure.repositories.tenants_repo import TenantRepository

DEFAULT_TENANT_NAME = "demo-workspace"
DEFAULT_INGESTION_KEY = "ing_demo_workspace_local_key"
DEFAULT_EVENT_COUNT = 30


def _ensure_demo_tenant_and_key() -> tuple[uuid.UUID, str]:
    with session_scope() as session:
        tenants_repo = TenantRepository(session)
        keys_repo = IngestionKeyRepository(session)

        tenant = tenants_repo.get_by_name(DEFAULT_TENANT_NAME)
        if tenant is None:
            tenant = tenants_repo.create(name=DEFAULT_TENANT_NAME)

        key_prefix = ingestion_key_prefix(DEFAULT_INGESTION_KEY)
        key_record = keys_repo.find_active_by_prefix(key_prefix)
        if key_record is None:
            keys_repo.create(
                tenant_id=tenant.id,
                key_prefix=key_prefix,
                key_hash=ingestion_key_hash(DEFAULT_INGESTION_KEY),
            )

        return tenant.id, DEFAULT_INGESTION_KEY


def _build_event_payload(index: int, now_utc: datetime) -> IngestEventRequest:
    event_type = ["page_view", "button_click", "signup", "purchase", "api_error"][index % 5]
    source = ["web", "mobile", "backend"][index % 3]
    severity = [None, "info", "warning", "error"][index % 4]

    occurred_at = now_utc - timedelta(minutes=(DEFAULT_EVENT_COUNT - index))
    user_id = f"user-{(index % 10) + 1}"
    session_id = f"sess-{(index % 6) + 1}"

    return IngestEventRequest(
        event_type=event_type,
        occurred_at=occurred_at,
        source=source,
        user_id=user_id,
        session_id=session_id,
        severity=severity,
        url=f"https://example.com/page/{index + 1}",
        referrer="https://google.com",
        schema_version="v1",
        attributes={"seeded": True, "index": index + 1},
    )


def populate(event_count: int = DEFAULT_EVENT_COUNT) -> None:
    tenant_id, ingest_key = _ensure_demo_tenant_and_key()

    accepted_count = 0
    duplicate_count = 0
    service = IngestionService()
    now_utc = datetime.now(UTC)

    with session_scope() as session:
        for index in range(event_count):
            payload = _build_event_payload(index=index, now_utc=now_utc)
            result = service.ingest_event(
                session=session,
                tenant_id=tenant_id,
                payload=payload,
                headers_jsonb={"x-seed-script": "populate_events.py"},
                ip="127.0.0.1",
                user_agent="populate-events-script/1.0",
            )
            if result.status == "accepted":
                accepted_count += 1
            else:
                duplicate_count += 1

    print("Populate completed")
    print(f"Tenant: {DEFAULT_TENANT_NAME} ({tenant_id})")
    print(f"Ingestion key: {ingest_key}")
    print(f"Requested inserts: {event_count}")
    print(f"Accepted: {accepted_count}")
    print(f"Duplicates: {duplicate_count}")


def main() -> None:
    populate(DEFAULT_EVENT_COUNT)


if __name__ == "__main__":
    main()
