"""linkedin account connect fields

Revision ID: 0009_linkedin_account_connect
Revises: 0008_app_settings
Create Date: 2026-05-20

"""

from alembic import op
import sqlalchemy as sa


revision = "0009_linkedin_account_connect"
down_revision = "0008_app_settings"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("linkedin_accounts", sa.Column("last_connected_at", sa.DateTime(timezone=True), nullable=True))
    op.alter_column("linkedin_accounts", "status", server_default="pending")


def downgrade() -> None:
    op.alter_column("linkedin_accounts", "status", server_default="inactive")
    op.drop_column("linkedin_accounts", "last_connected_at")

