import logging
from functools import lru_cache

from pydantic import Field, ValidationError, field_validator
from pydantic_core import ErrorDetails
from pydantic_settings import BaseSettings, SettingsConfigDict

logger = logging.getLogger(__name__)

MIN_JWT_SECRET_LENGTH = 32
POSTGRES_URL_PREFIX = "postgresql+psycopg://"
PLACEHOLDER_PREFIX = "PASTE"
DEFAULT_ENV_FILE = ".env"


class ConfigError(RuntimeError):
    """Bad environment configuration. The message names variables and rules, never values."""


def _check_postgres_url(value: str) -> str:
    if not value.startswith(POSTGRES_URL_PREFIX):
        raise ValueError(f"must start with {POSTGRES_URL_PREFIX}")
    return value


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=DEFAULT_ENV_FILE, env_file_encoding="utf-8", extra="ignore")

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

    @field_validator("database_url")
    @classmethod
    def required_postgres_url(cls, value: str) -> str:
        if not value.strip():
            raise ValueError("is required")
        return _check_postgres_url(value)

    @field_validator("database_url_direct")
    @classmethod
    def optional_postgres_url(cls, value: str | None) -> str | None:
        if value is None or not value.strip():
            return None
        return _check_postgres_url(value)

    @field_validator(
        "r2_account_id",
        "r2_access_key_id",
        "r2_secret_access_key",
        "r2_bucket",
        "r2_public_base_url",
        mode="before",
    )
    @classmethod
    def unset_placeholders(cls, value: str | None) -> str | None:
        if isinstance(value, str):
            stripped = value.strip()
            if not stripped or stripped.upper().startswith(PLACEHOLDER_PREFIX):
                return None
            return stripped
        return value

    @field_validator("frontend_url")
    @classmethod
    def exact_origins(cls, value: str) -> str:
        if "*" in value:
            raise ValueError("must list exact origins; '*' is not allowed")
        return value

    @property
    def frontend_origins(self) -> list[str]:
        return [o.strip().rstrip("/") for o in self.frontend_url.split(",") if o.strip()]

    @property
    def migration_database_url(self) -> str:
        return self.database_url_direct or self.database_url

    @property
    def r2_enabled(self) -> bool:
        return all(
            (self.r2_account_id, self.r2_access_key_id, self.r2_secret_access_key, self.r2_bucket)
        )


def _describe(error: ErrorDetails) -> str:
    """One readable rule per error. Uses only the field name and the rule, never the input."""
    name = str(error["loc"][0]).upper() if error["loc"] else "CONFIG"
    ctx = error.get("ctx") or {}
    kind = error["type"]
    if kind == "missing":
        return f"{name} is required"
    if kind == "string_too_short":
        return f"{name} must be at least {ctx.get('min_length')} characters"
    if kind == "greater_than":
        return f"{name} must be greater than {ctx.get('gt')}"
    if kind in ("int_parsing", "int_type"):
        return f"{name} must be a whole number"
    if kind == "value_error":
        return f"{name} {ctx.get('error')}"
    return f"{name} is invalid ({kind})"


def load_settings(env_file: str | None = DEFAULT_ENV_FILE) -> Settings:
    try:
        settings = Settings(_env_file=env_file)
    except ValidationError as exc:
        message = "Invalid configuration: " + "; ".join(_describe(e) for e in exc.errors())
        # Logged as well as raised so it is visible in the Vercel runtime log.
        logger.error(message)
        # `from None` drops the pydantic error, whose text includes the bad input values.
        raise ConfigError(message) from None
    return settings


@lru_cache
def get_settings() -> Settings:
    return load_settings()
