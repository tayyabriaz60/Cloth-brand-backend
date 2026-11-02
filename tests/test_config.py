import logging

import pytest

from app.core.config import ConfigError, load_settings

VALID_DB_URL = "postgresql+psycopg://user:pw@host-pooler/db?sslmode=require"
VALID_SECRET = "x" * 40
R2_VARS = (
    "R2_ACCOUNT_ID",
    "R2_ACCESS_KEY_ID",
    "R2_SECRET_ACCESS_KEY",
    "R2_BUCKET",
    "R2_PUBLIC_BASE_URL",
)


@pytest.fixture(autouse=True)
def valid_env(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("DATABASE_URL", VALID_DB_URL)
    monkeypatch.setenv("JWT_SECRET", VALID_SECRET)
    monkeypatch.setenv("FRONTEND_URL", "http://localhost:5173")
    for name in R2_VARS:
        monkeypatch.delenv(name, raising=False)


def config_error(monkeypatch: pytest.MonkeyPatch, **env: str) -> ConfigError:
    for name, value in env.items():
        monkeypatch.setenv(name, value)
    with pytest.raises(ConfigError) as caught:
        load_settings(env_file=None)
    return caught.value


def test_short_jwt_secret_names_the_rule_but_not_the_value(monkeypatch: pytest.MonkeyPatch) -> None:
    error = config_error(monkeypatch, JWT_SECRET="tooshort-secret-value")

    assert "JWT_SECRET must be at least 32 characters" in str(error)
    assert "tooshort-secret-value" not in str(error)
    assert error.__cause__ is None and error.__suppress_context__


def test_missing_database_url_is_reported(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("DATABASE_URL")
    with pytest.raises(ConfigError, match="DATABASE_URL is required"):
        load_settings(env_file=None)


def test_wrong_database_url_hides_the_url(monkeypatch: pytest.MonkeyPatch) -> None:
    secret_url = "postgresql://neondb_owner:hunter2@ep-x-pooler.neon.tech/db"
    error = config_error(monkeypatch, DATABASE_URL=secret_url)

    assert "DATABASE_URL must start with postgresql+psycopg://" in str(error)
    assert "hunter2" not in str(error)


def test_placeholder_database_url_is_rejected(monkeypatch: pytest.MonkeyPatch) -> None:
    error = config_error(monkeypatch, DATABASE_URL="PASTE_POOLED_NEON_URL_HERE")

    assert "DATABASE_URL must start with" in str(error)


def test_wildcard_frontend_url_is_rejected(monkeypatch: pytest.MonkeyPatch) -> None:
    error = config_error(monkeypatch, FRONTEND_URL="*")

    assert "FRONTEND_URL must list exact origins" in str(error)


def test_all_problems_are_listed_together(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("DATABASE_URL")
    error = config_error(monkeypatch, JWT_SECRET="short", JWT_EXPIRE_MINUTES="abc")

    message = str(error)
    assert "DATABASE_URL is required" in message
    assert "JWT_SECRET must be at least 32 characters" in message
    assert "JWT_EXPIRE_MINUTES must be a whole number" in message


def test_config_error_is_logged(monkeypatch: pytest.MonkeyPatch, caplog: pytest.LogCaptureFixture) -> None:
    with caplog.at_level(logging.ERROR, logger="app.core.config"):
        config_error(monkeypatch, JWT_SECRET="short-secret-xyz")

    assert "JWT_SECRET must be at least 32 characters" in caplog.text
    assert "short-secret-xyz" not in caplog.text


@pytest.mark.parametrize("value", ["", "   ", "PASTE_HERE", "paste_here", "PASTE"])
def test_r2_empty_or_placeholder_counts_as_unset(monkeypatch: pytest.MonkeyPatch, value: str) -> None:
    for name in R2_VARS:
        monkeypatch.setenv(name, value)

    settings = load_settings(env_file=None)

    assert settings.r2_account_id is None
    assert settings.r2_access_key_id is None
    assert settings.r2_secret_access_key is None
    assert settings.r2_bucket is None
    assert settings.r2_public_base_url is None
    assert settings.r2_enabled is False


def test_real_r2_values_enable_r2(monkeypatch: pytest.MonkeyPatch) -> None:
    for name in R2_VARS:
        monkeypatch.setenv(name, "real-value")

    assert load_settings(env_file=None).r2_enabled is True


def test_empty_direct_url_falls_back_to_database_url(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("DATABASE_URL_DIRECT", "")

    settings = load_settings(env_file=None)

    assert settings.database_url_direct is None
    assert settings.migration_database_url == VALID_DB_URL
