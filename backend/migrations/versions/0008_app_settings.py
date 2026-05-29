"""app settings

Revision ID: 0008_app_settings
Revises: 0007_email_enrichment
Create Date: 2026-05-19

"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


revision = "0008_app_settings"
down_revision = "0007_email_enrichment"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "app_settings",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, nullable=False),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("default_account_daily_limit", sa.Integer(), nullable=False, server_default="50"),
        sa.Column("max_connections_per_day", sa.Integer(), nullable=False, server_default="30"),
        sa.Column("max_messages_per_day", sa.Integer(), nullable=False, server_default="60"),
        sa.Column("max_profile_visits_per_day", sa.Integer(), nullable=False, server_default="80"),
        sa.Column("delay_min_ms", sa.Integer(), nullable=False, server_default="400"),
        sa.Column("delay_max_ms", sa.Integer(), nullable=False, server_default="1600"),
        sa.Column("proxy_url", sa.String(length=500), nullable=True),
        sa.Column("proxy_username", sa.String(length=200), nullable=True),
        sa.Column("proxy_password", sa.Text(), nullable=True),
        sa.Column("work_start_min_hour", sa.Integer(), nullable=False, server_default="8"),
        sa.Column("work_start_max_hour", sa.Integer(), nullable=False, server_default="11"),
        sa.Column("work_end_min_hour", sa.Integer(), nullable=False, server_default="16"),
        sa.Column("work_end_max_hour", sa.Integer(), nullable=False, server_default="21"),
        sa.Column("campaign_timezone", sa.String(length=60), nullable=False, server_default="UTC"),
        sa.Column(
            "campaign_work_days",
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=False,
            server_default=sa.text("'[]'::jsonb"),
        ),
        sa.Column("campaign_start_hour", sa.Integer(), nullable=False, server_default="9"),
        sa.Column("campaign_end_hour", sa.Integer(), nullable=False, server_default="17"),
        sa.Column(
            "blacklist_domains",
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=False,
            server_default=sa.text("'[]'::jsonb"),
        ),
        sa.Column(
            "blacklist_linkedin_urls",
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=False,
            server_default=sa.text("'[]'::jsonb"),
        ),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.UniqueConstraint("user_id", name="uq_app_settings_user"),
    )
    op.create_index("ix_app_settings_user_id", "app_settings", ["user_id"], unique=False)


def downgrade() -> None:
    op.drop_index("ix_app_settings_user_id", table_name="app_settings")
    op.drop_table("app_settings")

