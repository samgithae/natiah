import uuid

from pydantic import BaseModel, Field


class LeadCreate(BaseModel):
    account_id: uuid.UUID
    first_name: str | None = Field(default=None, max_length=120)
    last_name: str | None = Field(default=None, max_length=120)
    company: str | None = Field(default=None, max_length=250)
    job_title: str | None = Field(default=None, max_length=250)
    linkedin_url: str = Field(min_length=1, max_length=500)
    email: str | None = Field(default=None, max_length=320)
    status: str = Field(default="new", max_length=40)
    raw_data: dict | None = None


class LeadOut(BaseModel):
    id: uuid.UUID
    account_id: uuid.UUID
    first_name: str | None
    last_name: str | None
    company: str | None
    job_title: str | None
    linkedin_url: str
    email: str | None
    status: str
