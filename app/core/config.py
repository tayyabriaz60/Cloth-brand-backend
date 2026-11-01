from functools import lru_cache

from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

MIN_JWT_SECRET_LENGTH = 32


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    database_url: str
    database_url_direct: str | None = None
    jwt_secret: str = Field(min_length=MIN_JWT_SECRET_LENGTH)
    jwt_expire_minutes: int = Field(default=720, gt=0)
    frontend_url: str = "http://localhost:5173"

    r2_account_id: str | None = None
    r2_access_key_id: str | None = None
    r2_secret_access_key: str | None = None
    r2_bucket: str | None = None
    r2_public_base_url: str | None = None

    @field_validator(
        "database_url_direct",
        "r2_account_id",
        "r2_access_key_id",
        "r2_secret_access_key",
        "r2_bucket",
        "r2_public_base_url",
        mode="before",
    )
    @classmethod
    def empty_to_none(cls, value: str | None) -> str | None:
        if isinstance(value, str) and not value.strip():
            return None
        return value

    @property
    def frontend_origins(self) -> list[str]:
        origins = [o.strip().rstrip("/") for o in self.frontend_url.split(",") if o.strip()]
        if "*" in origins:
            raise ValueError("FRONTEND_URL must list exact origins, wildcard is not allowed")
        return origins

    @property
    def migration_database_url(self) -> str:
        return self.database_url_direct or self.database_url

    @property
    def r2_enabled(self) -> bool:
        return all(
            (self.r2_account_id, self.r2_access_key_id, self.r2_secret_access_key, self.r2_bucket)
        )


@lru_cache
def get_settings() -> Settings:
    return Settings()
