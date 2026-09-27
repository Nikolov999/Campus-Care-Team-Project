from __future__ import annotations

import pytest

from campuscare.config import ConfigurationError, Settings, normalise_database_url


def _clear_settings(monkeypatch) -> None:
    for key in (
        "APP_NAME",
        "APP_ENV",
        "DATABASE_URL",
        "ALLOWED_EMAIL_DOMAINS",
        "MAX_UPLOAD_MB",
    ):
        monkeypatch.delenv(key, raising=False)


def test_database_url_normalisation() -> None:
    assert normalise_database_url("postgres://u:p@host/db") == "postgresql+psycopg://u:p@host/db"
    assert normalise_database_url("postgresql://u:p@host/db") == "postgresql+psycopg://u:p@host/db"
    assert normalise_database_url("postgresql+psycopg://u:p@host/db") == "postgresql+psycopg://u:p@host/db"


def test_settings_require_database_url(monkeypatch) -> None:
    _clear_settings(monkeypatch)
    with pytest.raises(ConfigurationError, match="DATABASE_URL"):
        Settings.from_env()


def test_settings_parse_valid_environment(monkeypatch) -> None:
    _clear_settings(monkeypatch)
    monkeypatch.setenv("DATABASE_URL", "postgresql://user:pass@host/campuscare")
    monkeypatch.setenv("ALLOWED_EMAIL_DOMAINS", "@student.ncirl.ie, ncirl.ie")
    monkeypatch.setenv("MAX_UPLOAD_MB", "4")

    settings = Settings.from_env()

    assert settings.database_url.startswith("postgresql+psycopg://")
    assert settings.allowed_email_domains == ("student.ncirl.ie", "ncirl.ie")
    assert settings.max_upload_bytes == 4 * 1024 * 1024


def test_production_rejects_local_sqlite(monkeypatch) -> None:
    _clear_settings(monkeypatch)
    monkeypatch.setenv("APP_ENV", "production")
    monkeypatch.setenv("DATABASE_URL", "sqlite+pysqlite:///:memory:")

    with pytest.raises(ConfigurationError, match="Production must use"):
        Settings.from_env()


def test_invalid_upload_limit_has_clear_error(monkeypatch) -> None:
    _clear_settings(monkeypatch)
    monkeypatch.setenv("DATABASE_URL", "sqlite+pysqlite:///:memory:")
    monkeypatch.setenv("MAX_UPLOAD_MB", "large")

    with pytest.raises(ConfigurationError, match="whole number"):
        Settings.from_env()
