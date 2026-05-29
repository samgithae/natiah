"""anti detection state

Revision ID: 0003_anti_detection_state
Revises: 0002_automation_jobs
Create Date: 2026-05-19

"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


revision = "0003_anti_detection_state"
down_revision = "0002_automation_jobs"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "automation_account_states",
        sa.Column("account_id", postgresql.UUID(as_uuid=True), primary_key=True, nullable=False),
        sa.Column("paused_until", sa.DateTime(timezone=True), nullable=True),
        sa.Column("cooldown_until", sa.DateTime(timezone=True), nullable=True),
        sa.Column("risk_score", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("last_captcha_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["account_id"], ["linkedin_accounts.id"], ondelete="CASCADE"),
    )

    op.create_table(
        "automation_account_day_stats",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("account_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("day", sa.Date(), nullable=False),
        sa.Column("connections_sent", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("messages_sent", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("profile_visits", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("failures", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["account_id"], ["linkedin_accounts.id"], ondelete="CASCADE"),
        sa.UniqueConstraint("account_id", "day", name="uq_auto_stats_account_day"),
    )
    op.create_index(
        "ix_automation_account_day_stats_account_id",
        "automation_account_day_stats",
        ["account_id"],
        unique=False,
    )
    op.create_index(
        "ix_automation_account_day_stats_day",
        "automation_account_day_stats",
        ["day"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index("ix_automation_account_day_stats_day", table_name="automation_account_day_stats")
    op.drop_index("ix_automation_account_day_stats_account_id", table_name="automation_account_day_stats")
    op.drop_table("automation_account_day_stats")
    op.drop_table("automation_account_states")

