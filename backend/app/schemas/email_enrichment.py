from pydantic import BaseModel, Field


class EmailEnrichmentSettingsIn(BaseModel):
    hunter_api_key: str | None = None
    apollo_api_key: str | None = None
    prospeo_api_key: str | None = None


class EmailEnrichmentSettingsOut(BaseModel):
    hunter_api_key_set: bool
    apollo_api_key_set: bool
    prospeo_api_key_set: bool


class EmailEnrichmentRequest(BaseModel):
    lead_ids: list[str] = Field(default_factory=list)

