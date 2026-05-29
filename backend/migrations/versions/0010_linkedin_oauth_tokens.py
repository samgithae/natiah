"""linkedin oauth token fields

Revision ID: 0010_linkedin_oauth_tokens
Revises: 0009_linkedin_account_connect
Create Date: 2026-05-29

"""
from alembic import op
import sqlalchemy as sa


revision = "0010_linkedin_oauth_tokens"
down_revision = "0009_linkedin_account_connect"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "linkedin_accounts",
        sa.Column("li_access_token", sa.Text(), nullable=True),
    )
    op.add_column(
        "linkedin_accounts",
        sa.Column("li_refresh_token", sa.Text(), nullable=True),
    )
    op.add_column(
        "linkedin_accounts",
        sa.Column("li_token_expires_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.add_column(
        "linkedin_accounts",
        sa.Column("li_member_id", sa.String(50), nullable=True),
    )


def downgrade() -> None:
    op.drop_column("linkedin_accounts", "li_member_id")
    op.drop_column("linkedin_accounts", "li_token_expires_at")
    op.drop_column("linkedin_accounts", "li_refresh_token")
    op.drop_column("linkedin_accounts", "li_access_token")
