"""email enrichment

Revision ID: 0007_email_enrichment
Revises: 0006_mautic_settings
Create Date: 2026-05-19

"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


revision = "0007_email_enrichment"
down_revision = "0006_mautic_settings"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "email_enrichment_settings",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, nullable=False),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("hunter_api_key", sa.Text(), nullable=True),
        sa.Column("apollo_api_key", sa.Text(), nullable=True),
        sa.Column("prospeo_api_key", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.UniqueConstraint("user_id", name="uq_email_enrichment_settings_user"),
    )
    op.create_index("ix_email_enrichment_settings_user_id", "email_enrichment_settings", ["user_id"], unique=False)

    op.create_table(
        "email_enrichment_results",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, nullable=False),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("lead_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("provider", sa.String(length=40), nullable=False),
        sa.Column("email", sa.String(length=320), nullable=False),
        sa.Column("status", sa.String(length=40), nullable=False, server_default="unknown"),
        sa.Column("confidence", sa.Integer(), nullable=False, server_default="0"),
        sa.Column(
            "details",
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=False,
            server_default=sa.text("'{}'::jsonb"),
        ),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["lead_id"], ["leads.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
    )
    op.create_index("ix_email_enrichment_results_user_id", "email_enrichment_results", ["user_id"], unique=False)
    op.create_index("ix_email_enrichment_results_lead_id", "email_enrichment_results", ["lead_id"], unique=False)


def downgrade() -> None:
    op.drop_index("ix_email_enrichment_results_lead_id", table_name="email_enrichment_results")
    op.drop_index("ix_email_enrichment_results_user_id", table_name="email_enrichment_results")
    op.drop_table("email_enrichment_results")
    op.drop_index("ix_email_enrichment_settings_user_id", table_name="email_enrichment_settings")
    op.drop_table("email_enrichment_settings")

