"""Add read-path indexes for milestone 5 query and aggregate endpoints.

Revision ID: 20260306_0003
Revises: 20260306_0002
Create Date: 2026-03-06
"""

from __future__ import annotations

from alembic import op

# revision identifiers, used by Alembic.
revision = "20260306_0003"
down_revision = "20260306_0002"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_index(
        "ix_event_normalized_tenant_source_occurred_at",
        "event_normalized",
        ["tenant_id", "source", "occurred_at_utc"],
        unique=False,
    )
    op.create_index(
        "ix_event_normalized_tenant_severity_occurred_at",
        "event_normalized",
        ["tenant_id", "severity", "occurred_at_utc"],
        unique=False,
    )
    op.create_index(
        "ix_event_normalized_tenant_session_occurred_at",
        "event_normalized",
        ["tenant_id", "session_id", "occurred_at_utc"],
        unique=False,
    )
    op.create_index(
        "ix_event_enriched_tenant_geo_country_event_id",
        "event_enriched",
        ["tenant_id", "geo_country", "event_id"],
        unique=False,
    )
    op.create_index(
        "ix_event_enriched_tenant_is_bot_event_id",
        "event_enriched",
        ["tenant_id", "is_bot", "event_id"],
        unique=False,
    )
    op.create_index(
        "ix_event_raw_tenant_ingest_status_received_at",
        "event_raw",
        ["tenant_id", "ingest_status", "received_at"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index("ix_event_raw_tenant_ingest_status_received_at", table_name="event_raw")
    op.drop_index("ix_event_enriched_tenant_is_bot_event_id", table_name="event_enriched")
    op.drop_index("ix_event_enriched_tenant_geo_country_event_id", table_name="event_enriched")
    op.drop_index("ix_event_normalized_tenant_session_occurred_at", table_name="event_normalized")
    op.drop_index("ix_event_normalized_tenant_severity_occurred_at", table_name="event_normalized")
    op.drop_index("ix_event_normalized_tenant_source_occurred_at", table_name="event_normalized")

