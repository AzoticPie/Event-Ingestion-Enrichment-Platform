"""Normalization helpers shared across ingestion and query paths."""

from __future__ import annotations


def canonical_event_type(event_type: str) -> str:
    """Normalize event type to canonical storage/query representation."""
    return event_type.strip().lower().replace(" ", "_")

