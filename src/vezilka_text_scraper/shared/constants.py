"""Shared constants used across the corpus builder."""

from pathlib import Path

APP_VERSION = "0.1.0"

DEFAULT_APP_ENV = "development"
DEFAULT_APP_NAME = "vezilka-text-scraper"

DEFAULT_LOG_LEVEL = "INFO"
DEFAULT_LOG_COLOR = True
DEFAULT_LOG_FORMAT = "human"
DEFAULT_LOG_DEFAULT_COLOR = "cyan"
LOG_FORMAT_HUMAN = "human"
LOG_FORMAT_JSON = "json"

DEFAULT_MEDIAWIKI_API_URL = "https://mk.wikipedia.org/w/api.php"
DEFAULT_MEDIAWIKI_USER_AGENT = "VezilkaTextScraper/0.1.0"
DEFAULT_MEDIAWIKI_REQUEST_TIMEOUT_SECONDS = 30
DEFAULT_MEDIAWIKI_MAX_RETRIES = 3

DEFAULT_LANGUAGE = "mk"
DEFAULT_RECURSIVE_CATEGORY_CRAWL = True
DEFAULT_CATEGORY_MAX_DEPTH = 2
DEFAULT_TOTAL_ARTICLE_LIMIT = 100
DEFAULT_PER_CATEGORY_ARTICLE_LIMIT = None
DEFAULT_INCLUDE_REDIRECTS = False
DEFAULT_WIKIPEDIA_NAMESPACE = 0
DEFAULT_REQUEST_DELAY_SECONDS = 0.2
DEFAULT_CONTINUE_ON_ERROR = True
DEFAULT_SCRAPE_CONFIG_PATH = Path("configs/scrape.yaml")
DEFAULT_CLEAN_CONFIG_PATH = Path("configs/clean.yaml")
DEFAULT_CLEAN_INPUT_PATH = None
DEFAULT_MIN_WORD_COUNT = 100
DEFAULT_MIN_SECTION_WORD_COUNT = 10
DEFAULT_SKIP_DISAMBIGUATION_PAGES = True
DEFAULT_LOG_SKIPPED_ARTICLES = True
DEFAULT_CLEAN_OUTPUT_RUN_NAME = None
DEFAULT_DISPLAY_CONFIG_PATH = Path("configs/display.yaml")
DEFAULT_DISPLAY_INPUT_PATH = None
DEFAULT_DISPLAY_ARTICLE_LIMIT = 3
DEFAULT_DISPLAY_SOURCE = "file"
DEFAULT_PERSIST_CONFIG_PATH = Path("configs/persist.yaml")
DEFAULT_PERSIST_INPUT_PATH = None
DEFAULT_PERSIST_ARTICLE_LIMIT = None
DEFAULT_INIT_DATABASE_CONFIG_PATH = Path("configs/init_database.yaml")
DEFAULT_PIPELINE_CONFIG_PATH = Path("configs/pipeline.yaml")
DEFAULT_DATABASE_TYPE = "sqlite"

DEFAULT_SQLITE_DATABASE_PATH = Path("data/vezilka_corpus.db")
DEFAULT_POSTGRES_HOST = "localhost"
DEFAULT_POSTGRES_PORT = 5432
DEFAULT_POSTGRES_USER = "vezilka"
DEFAULT_POSTGRES_PASSWORD = "vezilka"
DEFAULT_POSTGRES_DATABASE = "vezilka"
DEFAULT_POSTGRES_SCHEMA = "public"

DEFAULT_RAW_DATA_DIR = Path("data/raw")
DEFAULT_PROCESSED_DATA_DIR = Path("data/processed")
DEFAULT_EXPORT_DATA_DIR = Path("data/exports")

WIKIPEDIA_CANONICAL_BASE_URL = "https://mk.wikipedia.org/wiki"

SUITABLE_WIKIPEDIA_CATEGORIES = frozenset(
    {
        "Биологија",
        "Географија",
        "Историја",
        "Култура",
        "Математика",
        "Наука",
        "Образование",
        "Спорт",
        "Технологија",
        "Уметност",
    }
)

STOP_SECTION_TITLES = frozenset(
    {
        "Белешки",
        "Видете исто така",
        "Извори",
        "Наводи",
        "Надворешни врски",
        "Поврзано",
        "Референци",
    }
)

DISAMBIGUATION_TITLE_MARKERS = frozenset(
    {
        "појаснување",
        "појаснителна",
        "појаснителница",
    }
)
