from pydantic import BaseModel, Field


class ConnectLinkOut(BaseModel):
    url: str


class ConnectCompleteIn(BaseModel):
    token: str = Field(min_length=10)
    li_at: str = Field(min_length=10)


class ConnectStatusOut(BaseModel):
    status: str
    detail: str | None = None
