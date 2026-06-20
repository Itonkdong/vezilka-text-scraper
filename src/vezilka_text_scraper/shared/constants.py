"""Shared constants used across the corpus builder."""

from pathlib import Path

APP_VERSION = "0.1.0"

DEFAULT_APP_ENV = "development"
DEFAULT_APP_NAME = "vezilka-text-scraper"

DEFAULT_LOG_LEVEL = "INFO"
DEFAULT_LOG_COLOR = True
DEFAULT_LOG_FORMAT = "human"
LOG_FORMAT_HUMAN = "human"
LOG_FORMAT_JSON = "json"

DEFAULT_MEDIAWIKI_API_URL = "https://mk.wikipedia.org/w/api.php"
DEFAULT_MEDIAWIKI_USER_AGENT = "VezilkaTextScraper/0.1.0"
DEFAULT_MEDIAWIKI_REQUEST_TIMEOUT_SECONDS = 30
DEFAULT_MEDIAWIKI_MAX_RETRIES = 3

DEFAULT_LANGUAGE = "mk"
DEFAULT_RECURSIVE_CATEGORY_CRAWL = True
DEFAULT_CATEGORY_MAX_DEPTH = 2

DEFAULT_DATABASE_URL = "sqlite:///data/vezilka_corpus.db"

DEFAULT_RAW_DATA_DIR = Path("data/raw")
DEFAULT_PROCESSED_DATA_DIR = Path("data/processed")
DEFAULT_EXPORT_DATA_DIR = Path("data/exports")

WIKIPEDIA_CANONICAL_BASE_URL = "https://mk.wikipedia.org/wiki"

STOP_SECTION_TITLES = frozenset(
    {
        "Белешки",
        "Видете исто така",
        "Извори",
        "Наводи",
        "Надворешни врски",
        "Референци",
    }
)
