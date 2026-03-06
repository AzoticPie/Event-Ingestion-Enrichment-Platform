"""Create enrichment and failed enrichment tables.

Revision ID: 20260306_0002
Revises: 20260303_0001
Create Date: 2026-03-06
"""

from __future__ import annotations

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = "20260306_0002"
down_revision = "20260303_0001"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "event_enriched",
        sa.Column("event_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("tenant_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("geo_country", sa.String(length=64), nullable=True),
        sa.Column("ua_browser", sa.String(length=128), nullable=True),
        sa.Column("ua_os", sa.String(length=128), nullable=True),
        sa.Column("ua_device", sa.String(length=128), nullable=True),
        sa.Column("url_host", sa.String(length=255), nullable=True),
        sa.Column("url_path", sa.Text(), nullable=True),
        sa.Column("referrer_domain", sa.String(length=255), nullable=True),
        sa.Column("is_bot", sa.Boolean(), nullable=False, server_default=sa.text("false")),
        sa.Column("schema_tag", sa.String(length=64), nullable=False, server_default=sa.text("'m4_baseline'")),
        sa.Column("enriched_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.ForeignKeyConstraint(["event_id"], ["event_raw.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["tenant_id"], ["tenant.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("event_id"),
    )
    op.create_index("ix_event_enriched_tenant_enriched_at", "event_enriched", ["tenant_id", "enriched_at"], unique=False)
    op.create_index("ix_event_enriched_tenant_geo_country", "event_enriched", ["tenant_id", "geo_country"], unique=False)
    op.create_index("ix_event_enriched_tenant_is_bot", "event_enriched", ["tenant_id", "is_bot"], unique=False)
    op.create_index("ix_event_enriched_tenant_url_host", "event_enriched", ["tenant_id", "url_host"], unique=False)

    op.create_table(
        "failed_enrichment",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("event_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("tenant_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("stage", sa.String(length=64), nullable=False),
        sa.Column("error_code", sa.String(length=64), nullable=False),
        sa.Column("error_message", sa.Text(), nullable=False),
        sa.Column("attempts", sa.Integer(), nullable=False),
        sa.Column("failed_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("next_retry_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("status", sa.String(length=32), nullable=False),
        sa.Column("last_task_id", sa.String(length=128), nullable=True),
        sa.ForeignKeyConstraint(["event_id"], ["event_raw.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["tenant_id"], ["tenant.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("event_id", name="uq_failed_enrichment_event_id"),
    )
    op.create_index(
        "ix_failed_enrichment_tenant_status_failed_at",
        "failed_enrichment",
        ["tenant_id", "status", "failed_at"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index("ix_failed_enrichment_tenant_status_failed_at", table_name="failed_enrichment")
    op.drop_table("failed_enrichment")

    op.drop_index("ix_event_enriched_tenant_url_host", table_name="event_enriched")
    op.drop_index("ix_event_enriched_tenant_is_bot", table_name="event_enriched")
    op.drop_index("ix_event_enriched_tenant_geo_country", table_name="event_enriched")
    op.drop_index("ix_event_enriched_tenant_enriched_at", table_name="event_enriched")
    op.drop_table("event_enriched")

