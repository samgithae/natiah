import uuid
from datetime import datetime

from pydantic import BaseModel, Field


class LinkedInAccountCreate(BaseModel):
    name: str = Field(min_length=1, max_length=200)
    linkedin_email: str | None = Field(default=None, max_length=320)
    daily_limit: int = Field(default=50, ge=0)


class LinkedInAccountUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=200)
    linkedin_email: str | None = Field(default=None, max_length=320)
    daily_limit: int | None = Field(default=None, ge=0)
    status: str | None = Field(default=None, max_length=40)
    last_connected_at: datetime | None = None


class LinkedInAccountOut(BaseModel):
    id: uuid.UUID
    name: str
    linkedin_email: str | None
    session_path: str | None
    daily_limit: int
    status: str
    last_connected_at: datetime | None = None
    created_at: datetime | None = None
    li_member_id: str | None = None
    li_token_expires_at: datetime | None = None
