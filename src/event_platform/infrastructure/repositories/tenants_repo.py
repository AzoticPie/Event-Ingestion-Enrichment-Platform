"""Tenant repository implementation."""

from __future__ import annotations

import uuid

from sqlalchemy import select
from sqlalchemy.orm import Session

from event_platform.infrastructure.db.models import Tenant


class TenantRepository:
    """Data access for tenant records."""

    def __init__(self, session: Session) -> None:
        self._session = session

    def create(self, name: str, status: str = "active") -> Tenant:
        tenant = Tenant(name=name, status=status)
        self._session.add(tenant)
        self._session.flush()
        return tenant

    def get_by_id(self, tenant_id: uuid.UUID) -> Tenant | None:
        return self._session.get(Tenant, tenant_id)

    def get_by_name(self, name: str) -> Tenant | None:
        stmt = select(Tenant).where(Tenant.name == name)
        return self._session.execute(stmt).scalar_one_or_none()

