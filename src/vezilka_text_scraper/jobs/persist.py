"""Cleaned article database persistence job."""

from __future__ import annotations

from pathlib import Path
from time import perf_counter
from typing import Any

from pydantic import BaseModel, ConfigDict, Field

from vezilka_text_scraper.adapters.article_jsonl import CleanedArticleJsonlReader
from vezilka_text_scraper.adapters.database import ArticleDatabaseAdapter
from vezilka_text_scraper.services.configuration import ConfigurationService
from vezilka_text_scraper.services.persist_config import PersistConfig
from vezilka_text_scraper.shared.constants import DEFAULT_PERSIST_CONFIG_PATH
from vezilka_text_scraper.shared.logger import colorize, get_logger

LOGGER = get_logger(__name__)


class PersistJobResult(BaseModel):
    """Result summary for a database persistence job."""

    model_config = ConfigDict(frozen=True)

    input_path: Path
    config_path: Path
    database_type: str
    database_url: str
    read_count: int = Field(ge=0)
    inserted_count: int = Field(ge=0)
    updated_count: int = Field(ge=0)
    section_count: int = Field(ge=0)
    wiki_category_link_count: int = Field(ge=0)
    source_category_link_count: int = Field(ge=0)
    initialized_database: bool = False
    batch_size: int = Field(ge=0)
    batch_count: int = Field(ge=0)
    duration_seconds: float


class WikipediaPersistJob:
    """Persist cleaned article JSONL records into a SQL database."""

    default_config_path = DEFAULT_PERSIST_CONFIG_PATH

    def __init__(
        self,
        configuration_service: ConfigurationService,
        reader: CleanedArticleJsonlReader,
    ) -> None:
        self._configuration_service = configuration_service
        self._reader = reader

    def run(
        self,
        config_path: Path | None = None,
        with_init: bool = False,
    ) -> PersistJobResult:
        """Run the persist job."""
        resolved_config_path = config_path or self.default_config_path
        started_at = perf_counter()
        input_path = Path("-")
        database_type = "-"
        database_url = "-"
        read_count = 0
        inserted_count = 0
        updated_count = 0
        section_count = 0
        wiki_category_link_count = 0
        source_category_link_count = 0
        batch_count = 0
        batch_size = 0

        try:
            config = self._configuration_service.load(resolved_config_path, PersistConfig)
            batch_size = config.batch_size
            database_type = config.database.type
            database_adapter = ArticleDatabaseAdapter(config.database)
            database_url = database_adapter.mask_database_url()
            if with_init:
                LOGGER.info(f"Initializing database before persist: {database_url}")
                database_adapter.initialize_schema()

            input_path = self._reader.resolve_input_path(config.input_path)
            LOGGER.info(f"Starting Wikipedia persist job from {input_path}")
            for articles in self._reader.iter_article_batches(
                input_path,
                config.batch_size,
                config.article_limit,
            ):
                batch_count += 1
                read_count += len(articles)
                LOGGER.info(f"Persisting cleaned batch of {len(articles)} articles")
                persisted = database_adapter.persist_articles(articles)
                inserted_count += persisted.inserted_count
                updated_count += persisted.updated_count
                section_count += persisted.section_count
                wiki_category_link_count += persisted.wiki_category_link_count
                source_category_link_count += persisted.source_category_link_count
            if batch_count == 0:
                database_adapter.validate_ready()

            result = PersistJobResult(
                input_path=input_path,
                config_path=resolved_config_path,
                database_type=database_type,
                database_url=database_url,
                read_count=read_count,
                inserted_count=inserted_count,
                updated_count=updated_count,
                section_count=section_count,
                wiki_category_link_count=wiki_category_link_count,
                source_category_link_count=source_category_link_count,
                initialized_database=with_init,
                batch_size=batch_size,
                batch_count=batch_count,
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
            result = PersistJobResult(
                input_path=input_path,
                config_path=resolved_config_path,
                database_type=database_type,
                database_url=database_url,
                read_count=read_count,
                inserted_count=inserted_count,
                updated_count=updated_count,
                section_count=section_count,
                wiki_category_link_count=wiki_category_link_count,
                source_category_link_count=source_category_link_count,
                initialized_database=with_init,
                batch_size=batch_size,
                batch_count=batch_count,
                duration_seconds=perf_counter() - started_at,
            )
            LOGGER.error(
                colorize(
                    self._format_final_summary(
                        status="FAILED",
                        result=result,
                        error=error,
                    ),
                    "red",
                )
            )
            raise

    def _format_final_summary(
        self,
        status: str,
        result: PersistJobResult,
        error: Exception | None = None,
    ) -> str:
        details: dict[str, Any] = {
            "Job": "persist",
            "Status": status,
            "Config": result.config_path,
            "Input": result.input_path,
            "Database": result.database_type,
            "DB URL": result.database_url,
            "Read": result.read_count,
            "Inserted": result.inserted_count,
            "Updated": result.updated_count,
            "Sections": result.section_count,
            "Wiki links": result.wiki_category_link_count,
            "Source links": result.source_category_link_count,
            "With init": result.initialized_database,
            "Batch size": result.batch_size,
            "Batches": result.batch_count,
            "Duration": f"{result.duration_seconds:.2f}s",
        }
        if error is not None:
            details["Reason"] = str(error)

        width = 80
        title = f" {status} JOB SUMMARY "
        border = f"+{title.center(width - 2, '=')}+"
        lines = ["", border]
        for key, value in details.items():
            lines.append(f"| {key:<14}: {str(value):<{width - 19}} |")
        lines.append(f"+{'=' * (width - 2)}+")
        return "\n".join(lines)


def build_wikipedia_persist_job() -> WikipediaPersistJob:
    """Build the persist job with production dependencies."""
    return WikipediaPersistJob(
        configuration_service=ConfigurationService(),
        reader=CleanedArticleJsonlReader(),
    )


def main(config_path: Path | None = None, with_init: bool = False) -> None:
    """Run the persist job."""
    import sys

    from vezilka_text_scraper.shared.logger import configure_logging

    resolved_config_path = config_path
    resolved_with_init = with_init
    cli_args = sys.argv[1:]
    if cli_args:
        if any(arg in {"-h", "--help"} for arg in cli_args):
            print("Usage: persist-wikipedia [--with-init] [config_path]")
            print(f"Default config: {WikipediaPersistJob.default_config_path}")
            return
        remaining_args: list[str] = []
        for arg in cli_args:
            if arg == "--with-init":
                resolved_with_init = True
            else:
                remaining_args.append(arg)
        if remaining_args:
            resolved_config_path = Path(remaining_args[0])

    configure_logging()
    result = build_wikipedia_persist_job().run(
        config_path=resolved_config_path,
        with_init=resolved_with_init,
    )
    print(
        f"Persisted {result.inserted_count} inserted and {result.updated_count} updated "
        f"articles from {result.input_path}"
    )


if __name__ == "__main__":
    main()
