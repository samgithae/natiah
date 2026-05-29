"""message events

Revision ID: 0005_message_events
Revises: 0004_sequence_engine
Create Date: 2026-05-19

"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql
from sqlalchemy import inspect


revision = "0005_message_events"
down_revision = "0004_sequence_engine"
branch_labels = None
depends_on = None


def upgrade() -> None:
    bind = op.get_bind()
    if inspect(bind).has_table("message_events"):
        return
    op.create_table(
        "message_events",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, nullable=False),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("campaign_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("lead_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("channel", sa.String(length=40), nullable=False),
        sa.Column("event_type", sa.String(length=60), nullable=False),
        sa.Column("status", sa.String(length=40), nullable=False, server_default="queued"),
        sa.Column("payload", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["campaign_id"], ["campaigns.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["lead_id"], ["leads.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
    )
    op.create_index("ix_message_events_user_id", "message_events", ["user_id"], unique=False)
    op.create_index("ix_message_events_campaign_id", "message_events", ["campaign_id"], unique=False)
    op.create_index("ix_message_events_lead_id", "message_events", ["lead_id"], unique=False)


def downgrade() -> None:
    op.drop_index("ix_message_events_lead_id", table_name="message_events")
    op.drop_index("ix_message_events_campaign_id", table_name="message_events")
    op.drop_index("ix_message_events_user_id", table_name="message_events")
    op.drop_table("message_events")
