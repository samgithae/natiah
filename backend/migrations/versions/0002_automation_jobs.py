"""automation jobs queue

Revision ID: 0002_automation_jobs
Revises: 0001_initial
Create Date: 2026-05-19

"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


revision = "0002_automation_jobs"
down_revision = "0001_initial"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "automation_jobs",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, nullable=False),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("account_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("job_type", sa.String(length=80), nullable=False),
        sa.Column(
            "payload",
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=False,
            server_default=sa.text("'{}'::jsonb"),
        ),
        sa.Column("status", sa.String(length=30), nullable=False, server_default="queued"),
        sa.Column("run_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("attempts", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("locked_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("locked_by", sa.String(length=120), nullable=True),
        sa.Column("last_error", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["account_id"], ["linkedin_accounts.id"], ondelete="CASCADE"),
    )
    op.create_index("ix_automation_jobs_user_id", "automation_jobs", ["user_id"], unique=False)
    op.create_index("ix_automation_jobs_account_id", "automation_jobs", ["account_id"], unique=False)
    op.create_index(
        "ix_automation_jobs_status_run_at",
        "automation_jobs",
        ["status", "run_at"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index("ix_automation_jobs_status_run_at", table_name="automation_jobs")
    op.drop_index("ix_automation_jobs_account_id", table_name="automation_jobs")
    op.drop_index("ix_automation_jobs_user_id", table_name="automation_jobs")
    op.drop_table("automation_jobs")

