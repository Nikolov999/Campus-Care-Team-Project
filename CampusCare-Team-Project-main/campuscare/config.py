from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path

from dotenv import load_dotenv

load_dotenv()


class ConfigurationError(RuntimeError):
    """Raised when required application configuration is missing or invalid."""


def normalise_database_url(database_url: str) -> str:
    """Convert provider-style PostgreSQL URLs to SQLAlchemy's psycopg URL."""
    database_url = database_url.strip()
    if database_url.startswith("postgres://"):
        return database_url.replace("postgres://", "postgresql+psycopg://", 1)
    if database_url.startswith("postgresql://"):
        return database_url.replace("postgresql://", "postgresql+psycopg://", 1)
    return database_url


@dataclass(frozen=True)
class Settings:
    app_name: str
    app_env: str
    database_url: str
    allowed_email_domains: tuple[str, ...]
    max_upload_bytes: int

    @classmethod
    def from_env(cls) -> "Settings":
        raw_database_url = os.getenv("DATABASE_URL", "").strip()
        if not raw_database_url:
            raise ConfigurationError(
                "DATABASE_URL is required. CampusCare is designed to use a server-hosted PostgreSQL database."
            )

        app_env = os.getenv("APP_ENV", "development").strip().lower() or "development"
        database_url = normalise_database_url(raw_database_url)
        if app_env == "production" and not database_url.startswith("postgresql+psycopg://"):
            raise ConfigurationError(
                "Production must use a PostgreSQL DATABASE_URL. SQLite is only permitted for local automated tests."
            )

        raw_domains = os.getenv("ALLOWED_EMAIL_DOMAINS", "ncirl.ie,student.ncirl.ie")
        domains = tuple(
            domain.strip().lower().lstrip("@")
            for domain in raw_domains.split(",")
            if domain.strip()
        )
        if not domains:
            raise ConfigurationError("At least one allowed email domain is required.")

        try:
            max_upload_mb = int(os.getenv("MAX_UPLOAD_MB", "2"))
        except ValueError as exc:
            raise ConfigurationError("MAX_UPLOAD_MB must be a whole number.") from exc
        if max_upload_mb < 1 or max_upload_mb > 10:
            raise ConfigurationError("MAX_UPLOAD_MB must be between 1 and 10.")

        return cls(
            app_name=os.getenv("APP_NAME", "CampusCare").strip() or "CampusCare",
            app_env=app_env,
            database_url=database_url,
            allowed_email_domains=domains,
            max_upload_bytes=max_upload_mb * 1024 * 1024,
        )


def project_root() -> Path:
    return Path(__file__).resolve().parent.parent
