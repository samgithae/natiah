import uuid

from pydantic import BaseModel, Field


class MessageSequenceCreate(BaseModel):
    campaign_id: uuid.UUID
    step_number: int = Field(ge=1)
    delay_days: int = Field(ge=0, default=0)
    action_type: str = Field(default="linkedin_message", max_length=40)
    email_subject: str | None = Field(default=None, max_length=200)
    message_template: str = Field(min_length=1)


class MessageSequenceUpdate(BaseModel):
    step_number: int | None = Field(default=None, ge=1)
    delay_days: int | None = Field(default=None, ge=0)
    action_type: str | None = Field(default=None, max_length=40)
    email_subject: str | None = Field(default=None, max_length=200)
    message_template: str | None = Field(default=None, min_length=1)


class MessageSequenceOut(BaseModel):
    id: uuid.UUID
    campaign_id: uuid.UUID
    step_number: int
    delay_days: int
    action_type: str
    email_subject: str | None
    message_template: str
