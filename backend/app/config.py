from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    port: int = Field(default=4000, alias="PORT")
    postgres_dsn: str = Field(
        default="postgresql://ims:ims_password@localhost:5432/ims",
        alias="POSTGRES_DSN",
    )
    redis_url: str = Field(default="redis://localhost:6379/0", alias="REDIS_URL")
    cors_origin: str = Field(default="http://localhost:5173", alias="CORS_ORIGIN")
    ingest_api_key: str | None = Field(default=None, alias="INGEST_API_KEY")
    max_body_bytes: int = Field(default=1_048_576, alias="MAX_BODY_BYTES")
    rate_limit_per_second: int = Field(default=1_000, alias="RATE_LIMIT_PER_SECOND")
    queue_max_size: int = Field(default=50_000, alias="QUEUE_MAX_SIZE")
    debounce_window_seconds: int = Field(default=10, alias="DEBOUNCE_WINDOW_SECONDS")


settings = Settings()
