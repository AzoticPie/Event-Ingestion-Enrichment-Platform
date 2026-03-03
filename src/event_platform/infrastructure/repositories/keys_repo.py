"""Ingestion key repository implementation."""

from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import select
from sqlalchemy.orm import Session

from event_platform.infrastructure.db.models import IngestionKey


class IngestionKeyRepository:
    """Data access for ingestion key records."""

    def __init__(self, session: Session) -> None:
        self._session = session

    def create(
        self,
        tenant_id: uuid.UUID,
        key_prefix: str,
        key_hash: str,
        is_active: bool = True,
    ) -> IngestionKey:
        ingestion_key = IngestionKey(
            tenant_id=tenant_id,
            key_prefix=key_prefix,
            key_hash=key_hash,
            is_active=is_active,
        )
        self._session.add(ingestion_key)
        self._session.flush()
        return ingestion_key

    def find_active_by_prefix(self, key_prefix: str) -> IngestionKey | None:
        stmt = select(IngestionKey).where(
            IngestionKey.key_prefix == key_prefix,
            IngestionKey.is_active.is_(True),
        )
        return self._session.execute(stmt).scalar_one_or_none()

    def touch_last_used(self, key_id: uuid.UUID, used_at: datetime) -> None:
        ingestion_key = self._session.get(IngestionKey, key_id)
        if ingestion_key is not None:
            ingestion_key.last_used_at = used_at

