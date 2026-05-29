"""mautic settings

Revision ID: 0006_mautic_settings
Revises: 0005_message_events
Create Date: 2026-05-19

"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


revision = "0006_mautic_settings"
down_revision = "0005_message_events"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "mautic_settings",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, nullable=False),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("mautic_url", sa.String(length=500), nullable=False),
        sa.Column("username", sa.String(length=200), nullable=True),
        sa.Column("password", sa.Text(), nullable=True),
        sa.Column("api_token", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.UniqueConstraint("user_id", name="uq_mautic_settings_user"),
    )
    op.create_index("ix_mautic_settings_user_id", "mautic_settings", ["user_id"], unique=False)


def downgrade() -> None:
    op.drop_index("ix_mautic_settings_user_id", table_name="mautic_settings")
    op.drop_table("mautic_settings")

