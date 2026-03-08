"""FastAPI dependencies for DB and auth context."""

from __future__ import annotations

import uuid
from dataclasses import dataclass

from fastapi import Depends, Header, HTTPException, status
from sqlalchemy.orm import Session

from event_platform.core.security import ingestion_key_prefix, verify_ingestion_key
from event_platform.infrastructure.db.session import get_session
from event_platform.infrastructure.repositories.keys_repo import IngestionKeyRepository


@dataclass(slots=True)
class AuthContext:
    """Authenticated tenant context resolved from ingestion key."""

    tenant_id: uuid.UUID
    ingestion_key_id: uuid.UUID


def get_authenticated_tenant(
    x_ingest_key: str | None = Header(default=None, alias="X-Ingest-Key"),
    session: Session = Depends(get_session),
) -> AuthContext:
    """Validate ingestion API key and return tenant context."""
    if not x_ingest_key:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail={"code": "auth_failed", "message": "Missing ingestion key"},
        )

    prefix = ingestion_key_prefix(x_ingest_key)
    key_repo = IngestionKeyRepository(session)
    key_record = key_repo.find_active_by_prefix(prefix)

    if key_record is None or not verify_ingestion_key(x_ingest_key, key_record.key_hash):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail={"code": "auth_failed", "message": "Invalid ingestion key"},
        )

    return AuthContext(tenant_id=key_record.tenant_id, ingestion_key_id=key_record.id)

