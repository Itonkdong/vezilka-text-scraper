"""Full Wikipedia corpus pipeline job."""

from __future__ import annotations

from pathlib import Path
from time import perf_counter
from typing import Any

from pydantic import BaseModel, ConfigDict, Field

from vezilka_text_scraper.adapters.article_jsonl import CleanedArticleJsonlWriter
from vezilka_text_scraper.adapters.database import ArticleDatabaseAdapter
from vezilka_text_scraper.adapters.raw_storage import RawArticleJsonlStorageAdapter
from vezilka_text_scraper.jobs.clean import WikipediaCleanJob, build_wikipedia_clean_job
from vezilka_text_scraper.jobs.scrape import WikipediaScrapeJob, build_wikipedia_scrape_job
from vezilka_text_scraper.models.article import CleanedArticle, RawArticleInput
from vezilka_text_scraper.services.article_display import ArticleDisplayService
from vezilka_text_scraper.services.clean_config import CleanConfig
from vezilka_text_scraper.services.configuration import ConfigurationService
from vezilka_text_scraper.services.display_config import DisplayConfig
from vezilka_text_scraper.services.persist_config import DatabaseType, PersistConfig
from vezilka_text_scraper.services.pipeline_config import PipelineConfig, PipelineDisplaySource
from vezilka_text_scraper.services.scrape_config import ScrapeConfig
from vezilka_text_scraper.shared.constants import DEFAULT_PIPELINE_CONFIG_PATH
from vezilka_text_scraper.shared.exceptions import VezilkaTextScraperError
from vezilka_text_scraper.shared.logger import colorize, get_logger

LOGGER = get_logger(__name__)


class PipelineJobResult(BaseModel):
    """Result summary for the full corpus pipeline job."""

    model_config = ConfigDict(frozen=True)

    config_path: Path
    scrape_config_path: Path
    clean_config_path: Path
    persist_config_path: Path
    display_config_path: Path
    raw_output_path: Path
    clean_output_path: Path
    save_scraped_articles: bool
    save_cleaned_articles: bool
    persist_to_database: bool
    persist_database_type: DatabaseType | None = None
    batch_size: int
    batch_count: int = Field(default=0, ge=0)
    run_display: bool
    display_source: PipelineDisplaySource
    raw_discovered_count: int = Field(default=0, ge=0)
    raw_fetched_count: int = Field(default=0, ge=0)
    raw_saved_count: int = Field(default=0, ge=0)
    raw_failed_count: int = Field(default=0, ge=0)
    clean_read_count: int = Field(default=0, ge=0)
    cleaned_count: int = Field(default=0, ge=0)
    clean_saved_count: int = Field(default=0, ge=0)
    clean_skipped_count: int = Field(default=0, ge=0)
    clean_failed_count: int = Field(default=0, ge=0)
    safe_count: int = Field(default=0, ge=0)
    caution_count: int = Field(default=0, ge=0)
    restricted_count: int = Field(default=0, ge=0)
    persist_inserted_count: int = Field(default=0, ge=0)
    persist_updated_count: int = Field(default=0, ge=0)
    displayed_count: int = Field(default=0, ge=0)
    duration_seconds: float


class WikipediaPipelineJob:
    """Run scrape, clean, optional persist, and optional display as one workflow."""

    default_config_path = DEFAULT_PIPELINE_CONFIG_PATH

    def __init__(
        self,
        configuration_service: ConfigurationService,
        scrape_job: WikipediaScrapeJob,
        clean_job: WikipediaCleanJob,
        raw_storage: RawArticleJsonlStorageAdapter,
        cleaned_writer: CleanedArticleJsonlWriter,
        display_service: ArticleDisplayService,
    ) -> None:
        self._configuration_service = configuration_service
        self._scrape_job = scrape_job
        self._clean_job = clean_job
        self._raw_storage = raw_storage
        self._cleaned_writer = cleaned_writer
        self._display_service = display_service

    def run(self, config_path: Path | None = None) -> PipelineJobResult:
        """Run the full Wikipedia corpus pipeline."""
        resolved_config_path = config_path or self.default_config_path
        started_at = perf_counter()
        result = self._empty_result(resolved_config_path)

        try:
            config = self._configuration_service.load(resolved_config_path, PipelineConfig)
            scrape_config = self._configuration_service.load(
                config.scrape_config_path,
                ScrapeConfig,
            )
            clean_config = self._configuration_service.load(
                config.clean_config_path,
                CleanConfig,
            )
            display_config = None
            if config.run_display:
                display_config = self._configuration_service.load(
                    config.display_config_path,
                    DisplayConfig,
                )

            LOGGER.info("Starting full Wikipedia corpus pipeline")
            raw_output_path = Path("-")
            raw_saved_count = 0
            if config.save_scraped_articles:
                raw_output_path = self._raw_storage.build_output_path(
                    scrape_config.output_run_name
                )

            clean_output_path = Path("-")
            clean_saved_count = 0
            if config.save_cleaned_articles:
                clean_output_path = self._cleaned_writer.build_output_path(
                    clean_config.output_run_name
                )

            persist_inserted_count = 0
            persist_updated_count = 0
            persist_database_type: DatabaseType | None = None
            database_adapter: ArticleDatabaseAdapter | None = None
            if config.persist_to_database:
                persist_config = self._configuration_service.load(
                    config.persist_config_path,
                    PersistConfig,
                )
                persist_database_type = persist_config.database.type
                database_adapter = ArticleDatabaseAdapter(persist_config.database)
                database_adapter.initialize_schema()

            raw_discovered_count = 0
            raw_failed_count = 0
            clean_read_count = 0
            cleaned_count = 0
            clean_skipped_count = 0
            clean_failed_count = 0
            safe_count = 0
            caution_count = 0
            restricted_count = 0
            batch_count = 0
            display_articles: list[CleanedArticle] = []
            display_page_ids: list[int] = []
            display_limit = display_config.article_limit if display_config is not None else 0
            raw_file_started = False
            clean_file_started = False
            result = result.model_copy(
                update={
                    "scrape_config_path": config.scrape_config_path,
                    "clean_config_path": config.clean_config_path,
                    "persist_config_path": config.persist_config_path,
                    "display_config_path": config.display_config_path,
                    "raw_output_path": raw_output_path,
                    "clean_output_path": clean_output_path,
                    "save_scraped_articles": config.save_scraped_articles,
                    "save_cleaned_articles": config.save_cleaned_articles,
                    "persist_to_database": config.persist_to_database,
                    "persist_database_type": persist_database_type,
                    "batch_size": config.batch_size,
                    "run_display": config.run_display,
                    "display_source": config.display_source,
                }
            )

            for raw_batch in self._scrape_job.iter_raw_article_batches(
                scrape_config,
                config.batch_size,
            ):
                batch_count += 1
                raw_discovered_count += raw_batch.discovered_count
                raw_failed_count += raw_batch.failed_count
                if config.save_scraped_articles:
                    raw_saved_count += self._raw_storage.write_article_batch(
                        raw_batch.raw_articles,
                        raw_output_path,
                        append=raw_file_started,
                    )
                    raw_file_started = True

                raw_inputs = [
                    RawArticleInput(**raw_article.model_dump())
                    for raw_article in raw_batch.raw_articles
                ]
                clean_collection = self._clean_job.clean_raw_articles(raw_inputs, clean_config)
                clean_read_count += clean_collection.read_count
                cleaned_count += clean_collection.cleaned_count
                clean_skipped_count += clean_collection.skipped_count
                clean_failed_count += clean_collection.failed_count
                safe_count += clean_collection.safe_count
                caution_count += clean_collection.caution_count
                restricted_count += clean_collection.restricted_count

                if config.save_cleaned_articles:
                    clean_saved_count += self._cleaned_writer.write_article_batch(
                        clean_collection.cleaned_articles,
                        clean_output_path,
                        append=clean_file_started,
                    )
                    clean_file_started = True

                if database_adapter is not None:
                    persisted = database_adapter.persist_articles(
                        clean_collection.cleaned_articles
                    )
                    persist_inserted_count += persisted.inserted_count
                    persist_updated_count += persisted.updated_count

                if config.run_display:
                    remaining_display_slots = display_limit - len(display_page_ids)
                    if remaining_display_slots > 0:
                        batch_display_articles = clean_collection.cleaned_articles[
                            :remaining_display_slots
                        ]
                        display_articles.extend(batch_display_articles)
                        display_page_ids.extend(
                            article.page_id for article in batch_display_articles
                        )

                result = result.model_copy(
                    update={
                        "batch_count": batch_count,
                        "raw_discovered_count": raw_discovered_count,
                        "raw_fetched_count": clean_read_count,
                        "raw_saved_count": raw_saved_count,
                        "raw_failed_count": raw_failed_count,
                        "clean_read_count": clean_read_count,
                        "cleaned_count": cleaned_count,
                        "clean_saved_count": clean_saved_count,
                        "clean_skipped_count": clean_skipped_count,
                        "clean_failed_count": clean_failed_count,
                        "safe_count": safe_count,
                        "caution_count": caution_count,
                        "restricted_count": restricted_count,
                        "persist_inserted_count": persist_inserted_count,
                        "persist_updated_count": persist_updated_count,
                    }
                )

            if config.save_scraped_articles and not raw_file_started:
                self._raw_storage.write_article_batch([], raw_output_path, append=False)
            if config.save_cleaned_articles and not clean_file_started:
                self._cleaned_writer.write_article_batch([], clean_output_path, append=False)

            if database_adapter is not None and batch_count == 0:
                database_adapter.validate_ready()

            displayed_count = 0
            if config.run_display and display_config is not None:
                articles_to_display = display_articles
                if config.display_source == "database" and database_adapter is not None:
                    articles_to_display = database_adapter.read_articles_by_page_ids(
                        display_page_ids,
                        display_config.article_limit,
                    )
                formatted_output = self._display_service.format_articles(articles_to_display)
                if formatted_output:
                    print(formatted_output)
                displayed_count = len(articles_to_display)

            result = PipelineJobResult(
                config_path=resolved_config_path,
                scrape_config_path=config.scrape_config_path,
                clean_config_path=config.clean_config_path,
                persist_config_path=config.persist_config_path,
                display_config_path=config.display_config_path,
                raw_output_path=raw_output_path,
                clean_output_path=clean_output_path,
                save_scraped_articles=config.save_scraped_articles,
                save_cleaned_articles=config.save_cleaned_articles,
                persist_to_database=config.persist_to_database,
                persist_database_type=persist_database_type,
                batch_size=config.batch_size,
                batch_count=batch_count,
                run_display=config.run_display,
                display_source=config.display_source,
                raw_discovered_count=raw_discovered_count,
                raw_fetched_count=clean_read_count,
                raw_saved_count=raw_saved_count,
                raw_failed_count=raw_failed_count,
                clean_read_count=clean_read_count,
                cleaned_count=cleaned_count,
                clean_saved_count=clean_saved_count,
                clean_skipped_count=clean_skipped_count,
                clean_failed_count=clean_failed_count,
                safe_count=safe_count,
                caution_count=caution_count,
                restricted_count=restricted_count,
                persist_inserted_count=persist_inserted_count,
                persist_updated_count=persist_updated_count,
                displayed_count=displayed_count,
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
            result = result.model_copy(update={"duration_seconds": perf_counter() - started_at})
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

    def _empty_result(self, config_path: Path) -> PipelineJobResult:
        return PipelineJobResult(
            config_path=config_path,
            scrape_config_path=Path("-"),
            clean_config_path=Path("-"),
            persist_config_path=Path("-"),
            display_config_path=Path("-"),
            raw_output_path=Path("-"),
            clean_output_path=Path("-"),
            save_scraped_articles=False,
            save_cleaned_articles=False,
            persist_to_database=False,
            persist_database_type=None,
            batch_size=0,
            run_display=False,
            display_source="file",
            duration_seconds=0,
        )

    def _format_final_summary(
        self,
        status: str,
        result: PipelineJobResult,
        error: Exception | None = None,
    ) -> str:
        details: dict[str, Any] = {
            "Job": "pipeline",
            "Status": status,
            "Config": result.config_path,
            "Scrape cfg": result.scrape_config_path,
            "Clean cfg": result.clean_config_path,
            "Persist cfg": result.persist_config_path,
            "Display cfg": result.display_config_path,
            "Save raw": result.save_scraped_articles,
            "Save clean": result.save_cleaned_articles,
            "Persist": result.persist_to_database,
            "DB type": result.persist_database_type or "-",
            "Batch size": result.batch_size,
            "Batches": result.batch_count,
            "Display": result.run_display,
            "Display src": result.display_source,
            "Raw output": result.raw_output_path,
            "Clean output": result.clean_output_path,
            "Raw found": result.raw_discovered_count,
            "Raw fetched": result.raw_fetched_count,
            "Raw saved": result.raw_saved_count,
            "Raw failed": result.raw_failed_count,
            "Cleaned": result.cleaned_count,
            "Clean saved": result.clean_saved_count,
            "Clean skip": result.clean_skipped_count,
            "Clean failed": result.clean_failed_count,
            "Safe": result.safe_count,
            "Caution": result.caution_count,
            "Restricted": result.restricted_count,
            "DB inserted": result.persist_inserted_count,
            "DB updated": result.persist_updated_count,
            "Displayed": result.displayed_count,
            "Duration": f"{result.duration_seconds:.2f}s",
        }
        if error is not None:
            details["Reason"] = str(error)

        width = 86
        title = f" {status} JOB SUMMARY "
        border = f"+{title.center(width - 2, '=')}+"
        lines = ["", border]
        for key, value in details.items():
            lines.append(f"| {key:<14}: {str(value):<{width - 19}} |")
        lines.append(f"+{'=' * (width - 2)}+")
        return "\n".join(lines)


def build_wikipedia_pipeline_job() -> WikipediaPipelineJob:
    """Build the full pipeline job with production dependencies."""
    return WikipediaPipelineJob(
        configuration_service=ConfigurationService(),
        scrape_job=build_wikipedia_scrape_job(),
        clean_job=build_wikipedia_clean_job(),
        raw_storage=RawArticleJsonlStorageAdapter(),
        cleaned_writer=CleanedArticleJsonlWriter(),
        display_service=ArticleDisplayService(),
    )


def main(config_path: Path | None = None) -> int:
    """Run the full pipeline job."""
    import sys

    from vezilka_text_scraper.shared.logger import configure_logging

    resolved_config_path = config_path
    if resolved_config_path is None and len(sys.argv) > 1:
        if sys.argv[1] in {"-h", "--help"}:
            print("Usage: pipeline-wikipedia [config_path]")
            print(f"Default config: {WikipediaPipelineJob.default_config_path}")
            return 0
        resolved_config_path = Path(sys.argv[1])

    configure_logging()
    try:
        result = build_wikipedia_pipeline_job().run(resolved_config_path)
    except VezilkaTextScraperError:
        return 1

    print(
        f"Pipeline cleaned {result.cleaned_count} articles "
        f"({result.raw_fetched_count} raw fetched)"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
