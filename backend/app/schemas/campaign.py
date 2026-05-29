import uuid

from pydantic import BaseModel, Field


class CampaignCreate(BaseModel):
    name: str = Field(min_length=1, max_length=200)
    daily_limit: int = Field(default=50, ge=0)


class CampaignUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=200)
    status: str | None = Field(default=None, max_length=40)
    daily_limit: int | None = Field(default=None, ge=0)


class CampaignOut(BaseModel):
    id: uuid.UUID
    name: str
    status: str
    daily_limit: int
