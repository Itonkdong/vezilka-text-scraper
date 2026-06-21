"""Environment variables loaded from `.env` and process environment."""

import os
from pathlib import Path

from dotenv import load_dotenv

from vezilka_text_scraper.shared.constants import (
    DEFAULT_APP_ENV,
    DEFAULT_APP_NAME,
    DEFAULT_EXPORT_DATA_DIR,
    DEFAULT_LANGUAGE,
    DEFAULT_LOG_COLOR,
    DEFAULT_LOG_DEFAULT_COLOR,
    DEFAULT_LOG_FORMAT,
    DEFAULT_LOG_LEVEL,
    DEFAULT_MEDIAWIKI_API_URL,
    DEFAULT_MEDIAWIKI_MAX_RETRIES,
    DEFAULT_MEDIAWIKI_REQUEST_TIMEOUT_SECONDS,
    DEFAULT_MEDIAWIKI_USER_AGENT,
    DEFAULT_POSTGRES_DATABASE,
    DEFAULT_POSTGRES_HOST,
    DEFAULT_POSTGRES_PASSWORD,
    DEFAULT_POSTGRES_PORT,
    DEFAULT_POSTGRES_SCHEMA,
    DEFAULT_POSTGRES_USER,
    DEFAULT_PROCESSED_DATA_DIR,
    DEFAULT_RAW_DATA_DIR,
    DEFAULT_SQLITE_DATABASE_PATH,
)
from vezilka_text_scraper.shared.exceptions import ConfigurationError


def _get_bool_env(name: str, default: bool) -> bool:
    raw_value = os.getenv(name)
    if raw_value is None:
        return default

    normalized_value = raw_value.strip().lower()
    if normalized_value in {"1", "true", "yes", "y", "on"}:
        return True
    if normalized_value in {"0", "false", "no", "n", "off"}:
        return False

    raise ConfigurationError(f"{name} must be a boolean value.")


def _get_int_env(name: str, default: int, minimum: int | None = None) -> int:
    raw_value = os.getenv(name)
    if raw_value is None:
        return default

    try:
        parsed_value = int(raw_value)
    except ValueError as error:
        raise ConfigurationError(f"{name} must be an integer value.") from error

    if minimum is not None and parsed_value < minimum:
        raise ConfigurationError(f"{name} must be greater than or equal to {minimum}.")

    return parsed_value


load_dotenv(dotenv_path=Path(".env"), override=False)

APP_ENV = os.getenv("APP_ENV", DEFAULT_APP_ENV)
APP_NAME = os.getenv("APP_NAME", DEFAULT_APP_NAME)

LOG_LEVEL = os.getenv("LOG_LEVEL", DEFAULT_LOG_LEVEL).strip().upper()
LOG_COLOR = _get_bool_env("LOG_COLOR", DEFAULT_LOG_COLOR)
LOG_FORMAT = os.getenv("LOG_FORMAT", DEFAULT_LOG_FORMAT).strip().lower()
LOG_DEFAULT_COLOR = os.getenv("LOG_DEFAULT_COLOR", DEFAULT_LOG_DEFAULT_COLOR).strip().lower()

MEDIAWIKI_API_URL = os.getenv("MEDIAWIKI_API_URL", DEFAULT_MEDIAWIKI_API_URL)
MEDIAWIKI_USER_AGENT = os.getenv("MEDIAWIKI_USER_AGENT", DEFAULT_MEDIAWIKI_USER_AGENT)
MEDIAWIKI_REQUEST_TIMEOUT_SECONDS = _get_int_env(
    "MEDIAWIKI_REQUEST_TIMEOUT_SECONDS",
    DEFAULT_MEDIAWIKI_REQUEST_TIMEOUT_SECONDS,
    minimum=1,
)
MEDIAWIKI_MAX_RETRIES = _get_int_env(
    "MEDIAWIKI_MAX_RETRIES",
    DEFAULT_MEDIAWIKI_MAX_RETRIES,
    minimum=0,
)

LANGUAGE = os.getenv("LANGUAGE", DEFAULT_LANGUAGE)

SQLITE_DATABASE_PATH = Path(os.getenv("SQLITE_DATABASE_PATH", str(DEFAULT_SQLITE_DATABASE_PATH)))

POSTGRES_HOST = os.getenv("POSTGRES_HOST", DEFAULT_POSTGRES_HOST)
POSTGRES_PORT = _get_int_env("POSTGRES_PORT", DEFAULT_POSTGRES_PORT, minimum=1)
POSTGRES_USER = os.getenv("POSTGRES_USER", DEFAULT_POSTGRES_USER)
POSTGRES_PASSWORD = os.getenv("POSTGRES_PASSWORD", DEFAULT_POSTGRES_PASSWORD)
POSTGRES_DATABASE = os.getenv("POSTGRES_DATABASE", DEFAULT_POSTGRES_DATABASE)
POSTGRES_SCHEMA = os.getenv("POSTGRES_SCHEMA", DEFAULT_POSTGRES_SCHEMA)

RAW_DATA_DIR = Path(os.getenv("RAW_DATA_DIR", str(DEFAULT_RAW_DATA_DIR)))
PROCESSED_DATA_DIR = Path(os.getenv("PROCESSED_DATA_DIR", str(DEFAULT_PROCESSED_DATA_DIR)))
EXPORT_DATA_DIR = Path(os.getenv("EXPORT_DATA_DIR", str(DEFAULT_EXPORT_DATA_DIR)))
