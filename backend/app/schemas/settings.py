from pydantic import BaseModel, Field


class AppSettingsOut(BaseModel):
    default_account_daily_limit: int

    max_connections_per_day: int
    max_messages_per_day: int
    max_profile_visits_per_day: int

    delay_min_ms: int
    delay_max_ms: int

    proxy_url: str | None
    proxy_username: str | None
    proxy_password_set: bool

    work_start_min_hour: int
    work_start_max_hour: int
    work_end_min_hour: int
    work_end_max_hour: int

    campaign_timezone: str
    campaign_work_days: list[int] = Field(default_factory=list)
    campaign_start_hour: int
    campaign_end_hour: int

    blacklist_domains: list[str] = Field(default_factory=list)
    blacklist_linkedin_urls: list[str] = Field(default_factory=list)


class AppSettingsIn(BaseModel):
    default_account_daily_limit: int | None = None

    max_connections_per_day: int | None = None
    max_messages_per_day: int | None = None
    max_profile_visits_per_day: int | None = None

    delay_min_ms: int | None = None
    delay_max_ms: int | None = None

    proxy_url: str | None = None
    proxy_username: str | None = None
    proxy_password: str | None = None

    work_start_min_hour: int | None = None
    work_start_max_hour: int | None = None
    work_end_min_hour: int | None = None
    work_end_max_hour: int | None = None

    campaign_timezone: str | None = None
    campaign_work_days: list[int] | None = None
    campaign_start_hour: int | None = None
    campaign_end_hour: int | None = None

    blacklist_domains: list[str] | None = None
    blacklist_linkedin_urls: list[str] | None = None

