"""Seed utility for local tenant and ingestion key bootstrap."""

from __future__ import annotations

import hashlib
import os
import secrets

from event_platform.infrastructure.repositories.keys_repo import IngestionKeyRepository
from event_platform.infrastructure.repositories.tenants_repo import TenantRepository
from event_platform.infrastructure.db.session import session_scope

DEFAULT_TENANT_NAME = "demo-workspace"


def _build_key_material(raw_key: str) -> tuple[str, str]:
    digest = hashlib.sha256(raw_key.encode("utf-8")).hexdigest()
    prefix = raw_key[:8]
    return prefix, digest


def seed() -> None:
    """Create a demo tenant and one ingestion key if missing."""
    raw_key = os.getenv("SEED_INGESTION_KEY") or "ing_demo_workspace_local_key"
    key_prefix, key_hash = _build_key_material(raw_key)

    with session_scope() as session:
        tenants_repo = TenantRepository(session)
        keys_repo = IngestionKeyRepository(session)

        tenant = tenants_repo.get_by_name(DEFAULT_TENANT_NAME)
        if tenant is None:
            tenant = tenants_repo.create(name=DEFAULT_TENANT_NAME)

        existing_key = keys_repo.find_active_by_prefix(key_prefix)
        if existing_key is None:
            keys_repo.create(tenant_id=tenant.id, key_prefix=key_prefix, key_hash=key_hash)
            print("Seed completed")
            print(f"Tenant: {tenant.name}")
            print(f"Ingestion key (displayed once): {raw_key}")
        else:
            print("Seed already present for prefix; no new key created")
            print(f"Tenant: {tenant.name}")
            print(f"Existing key prefix: {existing_key.key_prefix}")


def main() -> None:
    """Entrypoint for python -m execution."""
    seed()


if __name__ == "__main__":
    main()

