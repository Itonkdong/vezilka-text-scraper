"""Environment variables loaded from `.env` and process environment."""

import os
from pathlib import Path

from dotenv import load_dotenv

from vezilka_text_scraper.shared.constants import (
    DEFAULT_APP_ENV,
    DEFAULT_APP_NAME,
    DEFAULT_CATEGORY_MAX_DEPTH,
    DEFAULT_DATABASE_URL,
    DEFAULT_EXPORT_DATA_DIR,
    DEFAULT_LANGUAGE,
    DEFAULT_LOG_COLOR,
    DEFAULT_LOG_FORMAT,
    DEFAULT_LOG_LEVEL,
    DEFAULT_MEDIAWIKI_API_URL,
    DEFAULT_MEDIAWIKI_MAX_RETRIES,
    DEFAULT_MEDIAWIKI_REQUEST_TIMEOUT_SECONDS,
    DEFAULT_MEDIAWIKI_USER_AGENT,
    DEFAULT_PROCESSED_DATA_DIR,
    DEFAULT_RAW_DATA_DIR,
    DEFAULT_RECURSIVE_CATEGORY_CRAWL,
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
RECURSIVE_CATEGORY_CRAWL = _get_bool_env(
    "RECURSIVE_CATEGORY_CRAWL",
    DEFAULT_RECURSIVE_CATEGORY_CRAWL,
)
CATEGORY_MAX_DEPTH = _get_int_env("CATEGORY_MAX_DEPTH", DEFAULT_CATEGORY_MAX_DEPTH, minimum=0)

DATABASE_URL = os.getenv("DATABASE_URL", DEFAULT_DATABASE_URL)

RAW_DATA_DIR = Path(os.getenv("RAW_DATA_DIR", str(DEFAULT_RAW_DATA_DIR)))
PROCESSED_DATA_DIR = Path(os.getenv("PROCESSED_DATA_DIR", str(DEFAULT_PROCESSED_DATA_DIR)))
EXPORT_DATA_DIR = Path(os.getenv("EXPORT_DATA_DIR", str(DEFAULT_EXPORT_DATA_DIR)))
