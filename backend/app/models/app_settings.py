import uuid
from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, Integer, String, Text, UniqueConstraint, func
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class AppSettings(Base):
    __tablename__ = "app_settings"
    __table_args__ = (UniqueConstraint("user_id", name="uq_app_settings_user"),)

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), index=True, nullable=False
    )

    default_account_daily_limit: Mapped[int] = mapped_column(Integer, nullable=False, default=50)

    max_connections_per_day: Mapped[int] = mapped_column(Integer, nullable=False, default=30)
    max_messages_per_day: Mapped[int] = mapped_column(Integer, nullable=False, default=60)
    max_profile_visits_per_day: Mapped[int] = mapped_column(Integer, nullable=False, default=80)

    delay_min_ms: Mapped[int] = mapped_column(Integer, nullable=False, default=400)
    delay_max_ms: Mapped[int] = mapped_column(Integer, nullable=False, default=1600)

    proxy_url: Mapped[str | None] = mapped_column(String(500), nullable=True)
    proxy_username: Mapped[str | None] = mapped_column(String(200), nullable=True)
    proxy_password: Mapped[str | None] = mapped_column(Text, nullable=True)

    work_start_min_hour: Mapped[int] = mapped_column(Integer, nullable=False, default=8)
    work_start_max_hour: Mapped[int] = mapped_column(Integer, nullable=False, default=11)
    work_end_min_hour: Mapped[int] = mapped_column(Integer, nullable=False, default=16)
    work_end_max_hour: Mapped[int] = mapped_column(Integer, nullable=False, default=21)

    campaign_timezone: Mapped[str] = mapped_column(String(60), nullable=False, default="UTC")
    campaign_work_days: Mapped[list[int]] = mapped_column(JSONB, nullable=False, default=list)
    campaign_start_hour: Mapped[int] = mapped_column(Integer, nullable=False, default=9)
    campaign_end_hour: Mapped[int] = mapped_column(Integer, nullable=False, default=17)

    blacklist_domains: Mapped[list[str]] = mapped_column(JSONB, nullable=False, default=list)
    blacklist_linkedin_urls: Mapped[list[str]] = mapped_column(JSONB, nullable=False, default=list)

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False
    )
