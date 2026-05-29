from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=(".env", "backend/.env"), extra="ignore")

    project_name: str = "Natiah"
    api_v1_prefix: str = "/api/v1"

    database_url: str = Field(
        default="postgresql+asyncpg://natiah:natiah@postgres:5432/natiah",
        validation_alias="DATABASE_URL",
    )
    redis_url: str = Field(default="redis://redis:6379/0", validation_alias="REDIS_URL")

    jwt_secret: str = Field(default="change-me", validation_alias="JWT_SECRET")
    jwt_algorithm: str = Field(default="HS256", validation_alias="JWT_ALGORITHM")
    access_token_expire_minutes: int = Field(
        default=60 * 24 * 7,
        validation_alias="ACCESS_TOKEN_EXPIRE_MINUTES",
    )

    cors_origins: str = Field(default="*", validation_alias="CORS_ORIGINS")

    db_auto_create: bool = Field(default=False, validation_alias="DB_AUTO_CREATE")

    playwright_headless: bool = Field(default=True, validation_alias="PLAYWRIGHT_HEADLESS")
    automation_slow_mo_ms: int = Field(default=0, validation_alias="AUTOMATION_SLOW_MO_MS")

    linkedin_client_id: str = Field(default="", validation_alias="LINKEDIN_CLIENT_ID")
    linkedin_client_secret: str = Field(default="", validation_alias="LINKEDIN_CLIENT_SECRET")
    linkedin_callback_url: str = Field(
        default="http://localhost:3000/connect/linkedin/callback",
        validation_alias="LINKEDIN_CALLBACK_URL",
    )
    linkedin_scopes: str = Field(
        default="openid profile email w_member_social",
        validation_alias="LINKEDIN_SCOPES",
    )


settings = Settings()
