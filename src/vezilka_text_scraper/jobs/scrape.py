"""Wikipedia scraping job."""

from __future__ import annotations

from datetime import UTC, datetime
from pathlib import Path
from time import perf_counter
from typing import Any

from pydantic import BaseModel, ConfigDict

from vezilka_text_scraper.adapters.mediawiki import MediaWikiAdapter, RawArticle
from vezilka_text_scraper.adapters.raw_storage import RawArticleJsonlStorageAdapter
from vezilka_text_scraper.services.article_discovery import ArticleDiscoveryService
from vezilka_text_scraper.services.configuration import ConfigurationService
from vezilka_text_scraper.services.scrape_config import ScrapeConfig
from vezilka_text_scraper.shared import env_variables
from vezilka_text_scraper.shared.constants import DEFAULT_SCRAPE_CONFIG_PATH
from vezilka_text_scraper.shared.exceptions import AdapterError, JobError
from vezilka_text_scraper.shared.logger import colorize, get_logger

LOGGER = get_logger(__name__)


class ScrapeJobResult(BaseModel):
    """Result summary for a Wikipedia scrape job."""

    model_config = ConfigDict(frozen=True)

    output_path: Path
    config_path: Path
    discovered_count: int
    saved_count: int
    failed_count: int
    duration_seconds: float


class WikipediaScrapeJob:
    """Orchestrate raw Wikipedia article discovery, fetching, and JSONL storage."""

    default_config_path = DEFAULT_SCRAPE_CONFIG_PATH

    def __init__(
        self,
        configuration_service: ConfigurationService,
        discovery_service: ArticleDiscoveryService,
        mediawiki_adapter: MediaWikiAdapter,
        storage_adapter: RawArticleJsonlStorageAdapter,
    ) -> None:
        self._configuration_service = configuration_service
        self._discovery_service = discovery_service
        self._mediawiki_adapter = mediawiki_adapter
        self._storage_adapter = storage_adapter

    def run(self, config_path: Path | None = None) -> ScrapeJobResult:
        """Run the Wikipedia scrape job.

        Raises:
            JobError: If the job cannot complete.
        """
        resolved_config_path = config_path or self.default_config_path
        started_at = perf_counter()
        output_path: Path | None = None
        discovered_count = 0
        saved_count = 0
        failed_count = 0

        try:
            config = self._configuration_service.load(resolved_config_path, ScrapeConfig)
            output_path = self._storage_adapter.build_output_path(config.output_run_name)
            scraped_at = datetime.now(UTC).isoformat()

            LOGGER.info(f"Starting raw Wikipedia scrape from {len(config.categories)} categories")
            discovered_articles = self._discovery_service.discover(config)
            discovered_count = len(discovered_articles)
            LOGGER.info(f"Discovered {discovered_count} unique articles")

            raw_articles: list[RawArticle] = []

            for discovered_article in discovered_articles:
                try:
                    raw_article = self._mediawiki_adapter.fetch_raw_article(
                        page_id=discovered_article.page_id,
                        language=env_variables.LANGUAGE,
                        source_categories=discovered_article.source_categories,
                        scraped_at=scraped_at,
                        include_redirects=config.include_redirects,
                    )
                except AdapterError as error:
                    failed_count += 1
                    if config.continue_on_error:
                        LOGGER.warning(
                            f"Skipping article '{discovered_article.title}' "
                            f"({discovered_article.page_id}): {error}"
                        )
                        continue
                    raise JobError(
                        f"Could not fetch article '{discovered_article.title}' "
                        f"({discovered_article.page_id})"
                    ) from error

                if raw_article is not None:
                    raw_articles.append(raw_article)

            try:
                saved_count = self._storage_adapter.write_articles(raw_articles, output_path)
            except AdapterError as error:
                raise JobError("Could not save raw Wikipedia scrape output") from error

            duration_seconds = perf_counter() - started_at
            result = ScrapeJobResult(
                output_path=output_path,
                config_path=resolved_config_path,
                discovered_count=discovered_count,
                saved_count=saved_count,
                failed_count=failed_count,
                duration_seconds=duration_seconds,
            )
            LOGGER.info(
                colorize(
                    self._format_final_summary(status="SUCCESS", result=result),
                    "green",
                )
            )
            return result
        except Exception as error:
            duration_seconds = perf_counter() - started_at
            LOGGER.error(
                colorize(
                    self._format_final_summary(
                        status="FAILED",
                        result=ScrapeJobResult(
                            output_path=output_path or Path("-"),
                            config_path=resolved_config_path,
                            discovered_count=discovered_count,
                            saved_count=saved_count,
                            failed_count=failed_count,
                            duration_seconds=duration_seconds,
                        ),
                        error=error,
                    ),
                    "red",
                )
            )
            raise

    def _format_final_summary(
        self,
        status: str,
        result: ScrapeJobResult,
        error: Exception | None = None,
    ) -> str:
        details: dict[str, Any] = {
            "Job": "scrape",
            "Status": status,
            "Config": result.config_path,
            "Output": result.output_path,
            "Discovered": result.discovered_count,
            "Saved": result.saved_count,
            "Failed": result.failed_count,
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


def build_wikipedia_scrape_job() -> WikipediaScrapeJob:
    """Build the Wikipedia scrape job with production dependencies."""
    mediawiki_adapter = MediaWikiAdapter()
    return WikipediaScrapeJob(
        configuration_service=ConfigurationService(),
        discovery_service=ArticleDiscoveryService(mediawiki_adapter),
        mediawiki_adapter=mediawiki_adapter,
        storage_adapter=RawArticleJsonlStorageAdapter(),
    )


def main(config_path: Path | None = None) -> None:
    """Run the scrape job and print a compact result summary."""
    import sys

    from vezilka_text_scraper.shared.logger import configure_logging

    resolved_config_path = config_path
    if resolved_config_path is None and len(sys.argv) > 1:
        if sys.argv[1] in {"-h", "--help"}:
            print("Usage: scrape-wikipedia [config_path]")
            print(f"Default config: {WikipediaScrapeJob.default_config_path}")
            return
        resolved_config_path = Path(sys.argv[1])

    configure_logging()
    result = build_wikipedia_scrape_job().run(resolved_config_path)
    print(f"Saved {result.saved_count} raw articles to {result.output_path}")


if __name__ == "__main__":
    main()
