"""Security and hashing helpers."""

from __future__ import annotations

import hashlib
import hmac


def ingestion_key_prefix(raw_key: str) -> str:
    """Return stable key prefix used for indexed lookup."""
    return raw_key[:8]


def ingestion_key_hash(raw_key: str) -> str:
    """Return sha256 digest for ingestion key persistence/verification."""
    return hashlib.sha256(raw_key.encode("utf-8")).hexdigest()


def verify_ingestion_key(raw_key: str, stored_hash: str) -> bool:
    """Constant-time verification for raw key against stored hash."""
    calculated = ingestion_key_hash(raw_key)
    return hmac.compare_digest(calculated, stored_hash)

