from pydantic import BaseModel, Field


class MauticSettingsIn(BaseModel):
    mautic_url: str = Field(min_length=1, max_length=500)
    username: str | None = Field(default=None, max_length=200)
    password: str | None = None
    api_token: str | None = None


class MauticSettingsOut(BaseModel):
    mautic_url: str
    username: str | None
    password_set: bool
    api_token_set: bool


class MauticSyncRequest(BaseModel):
    lead_ids: list[str] = Field(default_factory=list)
    tags: list[str] = Field(default_factory=list)
    segment_ids: list[int] = Field(default_factory=list)

