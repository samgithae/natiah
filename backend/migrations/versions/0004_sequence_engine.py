"""sequence engine tables

Revision ID: 0004_sequence_engine
Revises: 0003_anti_detection_state
Create Date: 2026-05-19

"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


revision = "0004_sequence_engine"
down_revision = "0003_anti_detection_state"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "message_sequences",
        sa.Column("action_type", sa.String(length=40), nullable=False, server_default="linkedin_message"),
    )
    op.add_column(
        "message_sequences",
        sa.Column("email_subject", sa.String(length=200), nullable=True),
    )

    op.create_table(
        "sequence_enrollments",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, nullable=False),
        sa.Column("campaign_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("lead_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("status", sa.String(length=30), nullable=False, server_default="active"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["campaign_id"], ["campaigns.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["lead_id"], ["leads.id"], ondelete="CASCADE"),
        sa.UniqueConstraint("campaign_id", "lead_id", name="uq_enrollment_campaign_lead"),
    )
    op.create_index("ix_sequence_enrollments_campaign_id", "sequence_enrollments", ["campaign_id"], unique=False)
    op.create_index("ix_sequence_enrollments_lead_id", "sequence_enrollments", ["lead_id"], unique=False)

    op.create_table(
        "sequence_actions",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, nullable=False),
        sa.Column("enrollment_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("campaign_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("lead_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("action_type", sa.String(length=40), nullable=False),
        sa.Column("step_number", sa.Integer(), nullable=False),
        sa.Column("scheduled_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("executed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("status", sa.String(length=30), nullable=False, server_default="queued"),
        sa.Column("attempts", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("last_error", sa.Text(), nullable=True),
        sa.Column(
            "payload",
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=False,
            server_default=sa.text("'{}'::jsonb"),
        ),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["campaign_id"], ["campaigns.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["enrollment_id"], ["sequence_enrollments.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["lead_id"], ["leads.id"], ondelete="CASCADE"),
        sa.UniqueConstraint("enrollment_id", "step_number", name="uq_action_enrollment_step"),
    )
    op.create_index("ix_sequence_actions_enrollment_id", "sequence_actions", ["enrollment_id"], unique=False)
    op.create_index("ix_sequence_actions_campaign_id", "sequence_actions", ["campaign_id"], unique=False)
    op.create_index("ix_sequence_actions_lead_id", "sequence_actions", ["lead_id"], unique=False)
    op.create_index("ix_sequence_actions_scheduled_at", "sequence_actions", ["scheduled_at"], unique=False)


def downgrade() -> None:
    op.drop_index("ix_sequence_actions_scheduled_at", table_name="sequence_actions")
    op.drop_index("ix_sequence_actions_lead_id", table_name="sequence_actions")
    op.drop_index("ix_sequence_actions_campaign_id", table_name="sequence_actions")
    op.drop_index("ix_sequence_actions_enrollment_id", table_name="sequence_actions")
    op.drop_table("sequence_actions")
    op.drop_index("ix_sequence_enrollments_lead_id", table_name="sequence_enrollments")
    op.drop_index("ix_sequence_enrollments_campaign_id", table_name="sequence_enrollments")
    op.drop_table("sequence_enrollments")
    op.drop_column("message_sequences", "email_subject")
    op.drop_column("message_sequences", "action_type")

