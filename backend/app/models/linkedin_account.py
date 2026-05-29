import uuid
from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, Integer, String, Text, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class LinkedInAccount(Base):
    __tablename__ = "linkedin_accounts"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), index=True, nullable=False
    )
    name: Mapped[str] = mapped_column(String(200), nullable=False)
    linkedin_email: Mapped[str | None] = mapped_column(String(320), nullable=True)
    session_path: Mapped[str | None] = mapped_column(String(500), nullable=True)
    daily_limit: Mapped[int] = mapped_column(Integer, default=50, nullable=False)
    status: Mapped[str] = mapped_column(String(40), default="pending", nullable=False)
    last_active: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    last_connected_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    li_access_token: Mapped[str | None] = mapped_column(Text, nullable=True)
    li_refresh_token: Mapped[str | None] = mapped_column(Text, nullable=True)
    li_token_expires_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    li_member_id: Mapped[str | None] = mapped_column(String(50), nullable=True)
