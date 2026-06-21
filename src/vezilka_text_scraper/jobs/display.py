"""Processed article display job."""

from __future__ import annotations

from pathlib import Path
from random import sample
from time import perf_counter
from typing import Any

from pydantic import BaseModel, ConfigDict

from vezilka_text_scraper.adapters.article_jsonl import CleanedArticleJsonlReader
from vezilka_text_scraper.adapters.database import ArticleDatabaseAdapter
from vezilka_text_scraper.models.article import CleanedArticle
from vezilka_text_scraper.services.article_display import ArticleDisplayService
from vezilka_text_scraper.services.configuration import ConfigurationService
from vezilka_text_scraper.services.display_config import DisplayConfig, DisplaySource
from vezilka_text_scraper.services.persist_config import DatabaseConfig, DatabaseType
from vezilka_text_scraper.shared.constants import DEFAULT_DISPLAY_CONFIG_PATH
from vezilka_text_scraper.shared.logger import colorize, get_logger

LOGGER = get_logger(__name__)
DISPLAY_SOURCE_FILE: DisplaySource = "file"
DISPLAY_SOURCE_SQLITE: DisplaySource = "sqlite"
DISPLAY_SOURCE_POSTGRESQL: DisplaySource = "postgresql"
DATABASE_DISPLAY_SOURCES = {DISPLAY_SOURCE_SQLITE, DISPLAY_SOURCE_POSTGRESQL}


class DisplayJobResult(BaseModel):
    """Result summary for a processed article display job."""

    model_config = ConfigDict(frozen=True)

    input_path: Path
    config_path: Path
    source: DisplaySource
    random_sample: bool
    read_count: int
    displayed_count: int
    duration_seconds: float


class WikipediaDisplayJob:
    """Print cleaned articles in a human-readable console format."""

    default_config_path = DEFAULT_DISPLAY_CONFIG_PATH

    def __init__(
        self,
        configuration_service: ConfigurationService,
        reader: CleanedArticleJsonlReader,
        display_service: ArticleDisplayService,
    ) -> None:
        self._configuration_service = configuration_service
        self._reader = reader
        self._display_service = display_service

    def run(
        self,
        config_path: Path | None = None,
        source: DisplaySource | None = None,
    ) -> DisplayJobResult:
        """Run the processed article display job."""
        resolved_config_path = config_path or self.default_config_path
        started_at = perf_counter()
        input_path = Path("-")
        resolved_source: DisplaySource = source or DISPLAY_SOURCE_FILE
        read_count = 0

        try:
            config = self._configuration_service.load(resolved_config_path, DisplayConfig)
            resolved_source = source or config.source
            if resolved_source in DATABASE_DISPLAY_SOURCES:
                database_adapter = ArticleDatabaseAdapter(
                    DatabaseConfig(type=self._database_type_for_source(resolved_source))
                )
                articles = database_adapter.read_articles(
                    None if config.random_sample else config.article_limit
                )
            else:
                resolved_source = DISPLAY_SOURCE_FILE
                input_path = self._reader.resolve_input_path(config.input_path)
                articles = self._reader.read_articles(
                    input_path,
                    None if config.random_sample else config.article_limit,
                )
            read_count = len(articles)
            display_articles = self._select_articles(
                articles,
                article_limit=config.article_limit,
                random_sample=config.random_sample,
            )
            formatted_output = self._display_service.format_articles(display_articles)
            if formatted_output:
                print(formatted_output)

            result = DisplayJobResult(
                input_path=input_path,
                config_path=resolved_config_path,
                source=resolved_source,
                random_sample=config.random_sample,
                read_count=read_count,
                displayed_count=len(display_articles),
                duration_seconds=perf_counter() - started_at,
            )
            LOGGER.info(
                colorize(
                    self._format_final_summary(status="SUCCESS", result=result),
                    "green",
                )
            )
            return result
        except Exception as error:
            result = DisplayJobResult(
                input_path=input_path,
                config_path=resolved_config_path,
                source=resolved_source,
                random_sample=False,
                read_count=read_count,
                displayed_count=read_count,
                duration_seconds=perf_counter() - started_at,
            )
            LOGGER.error(
                colorize(
                    self._format_final_summary(status="FAILED", result=result, error=error),
                    "red",
                )
            )
            raise

    def _format_final_summary(
        self,
        status: str,
        result: DisplayJobResult,
        error: Exception | None = None,
    ) -> str:
        details: dict[str, Any] = {
            "Job": "display",
            "Status": status,
            "Config": result.config_path,
            "Source": result.source,
            "Random": result.random_sample,
            "Input": result.input_path,
            "Read": result.read_count,
            "Displayed": result.displayed_count,
            "Duration": f"{result.duration_seconds:.2f}s",
        }
        if error is not None:
            details["Reason"] = str(error)

        width = 72
        title = f" {status} JOB SUMMARY "
        border = f"+{title.center(width - 2, '=')}+"
        lines = ["", border]
        for key, value in details.items():
            lines.append(f"| {key:<12}: {str(value):<{width - 17}} |")
        lines.append(f"+{'=' * (width - 2)}+")
        return "\n".join(lines)

    def _select_articles(
        self,
        articles: list[CleanedArticle],
        article_limit: int,
        random_sample: bool,
    ) -> list[CleanedArticle]:
        if not random_sample:
            return articles[:article_limit]
        if len(articles) <= article_limit:
            return articles
        return sample(articles, article_limit)

    def _database_type_for_source(self, source: DisplaySource) -> DatabaseType:
        if source == DISPLAY_SOURCE_SQLITE:
            return "sqlite"
        if source == DISPLAY_SOURCE_POSTGRESQL:
            return "postgresql"
        raise ValueError(f"Display source is not a database source: {source}")


def build_wikipedia_display_job() -> WikipediaDisplayJob:
    """Build the processed article display job with production dependencies."""
    return WikipediaDisplayJob(
        configuration_service=ConfigurationService(),
        reader=CleanedArticleJsonlReader(),
        display_service=ArticleDisplayService(),
    )


def main(config_path: Path | None = None, source: DisplaySource | None = None) -> None:
    """Run the display job."""
    import sys

    from vezilka_text_scraper.shared.logger import configure_logging

    resolved_config_path = config_path
    resolved_source = source
    cli_args = sys.argv[1:]
    if cli_args:
        if any(arg in {"-h", "--help"} for arg in cli_args):
            print(
                "Usage: display-wikipedia "
                "[--from-file|--from-sqlite|--from-postgres] [config_path]"
            )
            print(f"Default config: {WikipediaDisplayJob.default_config_path}")
            return
        remaining_args: list[str] = []
        for arg in cli_args:
            if arg == "--from-db":
                print("Use --from-sqlite or --from-postgres; --from-db is ambiguous.")
                return
            if arg == "--from-sqlite":
                resolved_source = DISPLAY_SOURCE_SQLITE
            elif arg == "--from-postgres":
                resolved_source = DISPLAY_SOURCE_POSTGRESQL
            elif arg == "--from-file":
                resolved_source = DISPLAY_SOURCE_FILE
            else:
                remaining_args.append(arg)
        if remaining_args:
            resolved_config_path = Path(remaining_args[0])

    configure_logging()
    build_wikipedia_display_job().run(
        config_path=resolved_config_path,
        source=resolved_source,
    )


if __name__ == "__main__":
    main()
