"""Wikipedia cleaning job."""

from __future__ import annotations

from datetime import UTC, datetime
from pathlib import Path
from time import perf_counter
from typing import Any

from pydantic import BaseModel, ConfigDict

from vezilka_text_scraper.adapters.article_jsonl import (
    CleanedArticleJsonlWriter,
    RawArticleJsonlReader,
)
from vezilka_text_scraper.models.article import CleanedArticle, RawArticleInput
from vezilka_text_scraper.services.article_cleaning import ArticleCleaningService
from vezilka_text_scraper.services.clean_config import CleanConfig
from vezilka_text_scraper.services.configuration import ConfigurationService
from vezilka_text_scraper.shared.constants import (
    DEFAULT_CLEAN_CONFIG_PATH,
    SENSITIVITY_STATUS_SAFE,
)
from vezilka_text_scraper.shared.exceptions import AdapterError, JobError, ServiceError
from vezilka_text_scraper.shared.logger import colorize, get_logger

LOGGER = get_logger(__name__)


class CleanJobResult(BaseModel):
    """Result summary for a Wikipedia clean job."""

    model_config = ConfigDict(frozen=True)

    input_path: Path
    output_path: Path
    config_path: Path
    read_count: int
    cleaned_count: int
    skipped_count: int
    failed_count: int
    batch_size: int
    batch_count: int
    duration_seconds: float


class CleanCollectionResult(BaseModel):
    """Cleaned articles before optional processed JSONL storage."""

    model_config = ConfigDict(frozen=True)

    cleaned_articles: list[CleanedArticle]
    read_count: int
    cleaned_count: int
    skipped_count: int
    failed_count: int


class WikipediaCleanJob:
    """Orchestrate raw article loading, MediaWiki cleaning, filtering, and JSONL storage."""

    default_config_path = DEFAULT_CLEAN_CONFIG_PATH

    def __init__(
        self,
        configuration_service: ConfigurationService,
        raw_reader: RawArticleJsonlReader,
        cleaning_service: ArticleCleaningService,
        cleaned_writer: CleanedArticleJsonlWriter,
    ) -> None:
        self._configuration_service = configuration_service
        self._raw_reader = raw_reader
        self._cleaning_service = cleaning_service
        self._cleaned_writer = cleaned_writer

    def run(self, config_path: Path | None = None) -> CleanJobResult:
        """Run the Wikipedia clean job.

        Raises:
            JobError: If the job cannot complete.
        """
        resolved_config_path = config_path or self.default_config_path
        started_at = perf_counter()
        input_path = Path("-")
        output_path = Path("-")
        read_count = 0
        cleaned_count = 0
        skipped_count = 0
        failed_count = 0
        batch_count = 0
        batch_size = 0

        try:
            config = self._configuration_service.load(resolved_config_path, CleanConfig)
            batch_size = config.batch_size
            input_path = self._raw_reader.resolve_input_path(config.input_path)
            output_path = self._cleaned_writer.build_output_path(config.output_run_name)
            LOGGER.info(f"Starting Wikipedia clean job from {input_path}")
            append = False
            for raw_batch in self._raw_reader.iter_article_batches(
                input_path,
                config.batch_size,
            ):
                batch_count += 1
                collected = self.clean_raw_articles(raw_batch, config)
                read_count += collected.read_count
                cleaned_count += collected.cleaned_count
                skipped_count += collected.skipped_count
                failed_count += collected.failed_count
                try:
                    self._cleaned_writer.write_article_batch(
                        collected.cleaned_articles,
                        output_path,
                        append=append,
                    )
                    append = True
                except AdapterError as error:
                    raise JobError("Could not save cleaned Wikipedia output") from error
            if batch_count == 0:
                try:
                    self._cleaned_writer.write_article_batch([], output_path, append=False)
                except AdapterError as error:
                    raise JobError("Could not save cleaned Wikipedia output") from error

            duration_seconds = perf_counter() - started_at
            result = CleanJobResult(
                input_path=input_path,
                output_path=output_path,
                config_path=resolved_config_path,
                read_count=read_count,
                cleaned_count=cleaned_count,
                skipped_count=skipped_count,
                failed_count=failed_count,
                batch_size=batch_size,
                batch_count=batch_count,
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
                        result=CleanJobResult(
                            input_path=input_path,
                            output_path=output_path,
                            config_path=resolved_config_path,
                            read_count=read_count,
                            cleaned_count=cleaned_count,
                            skipped_count=skipped_count,
                            failed_count=failed_count,
                            batch_size=batch_size,
                            batch_count=batch_count,
                            duration_seconds=duration_seconds,
                        ),
                        error=error,
                    ),
                    "red",
                )
            )
            raise

    def clean_raw_articles(
        self,
        raw_articles: list[RawArticleInput],
        config: CleanConfig,
    ) -> CleanCollectionResult:
        """Clean raw article records without writing processed JSONL."""
        read_count = len(raw_articles)
        cleaned_count = 0
        skipped_count = 0
        failed_count = 0
        cleaned_at = datetime.now(UTC).isoformat()

        LOGGER.info(f"Loaded {read_count} raw articles")

        cleaned_articles: list[CleanedArticle] = []
        for raw_article in raw_articles:
            try:
                candidate = self._cleaning_service.clean_article(
                    raw_article,
                    config,
                    cleaned_at,
                )
                skip_reason = self._cleaning_service.get_skip_reason(candidate, config)
                if skip_reason is not None:
                    skipped_count += 1
                    if config.log_skipped_articles:
                        LOGGER.info(
                            f"Skipping cleaned article '{raw_article.title}' "
                            f"({raw_article.page_id}): {skip_reason}"
                        )
                    continue
                if candidate.article.sensitivity_status != SENSITIVITY_STATUS_SAFE:
                    LOGGER.warning(
                        f"Sensitive article flagged as "
                        f"{candidate.article.sensitivity_status}: "
                        f"'{raw_article.title}' ({raw_article.page_id}); "
                        f"keywords={candidate.article.sensitivity_keywords}"
                    )
                cleaned_articles.append(candidate.article)
            except ServiceError as error:
                failed_count += 1
                LOGGER.warning(
                    f"Failed cleaning raw article '{raw_article.title}' "
                    f"({raw_article.page_id}): {error}"
                )
                if config.continue_on_error:
                    continue
                raise JobError(
                    f"Could not clean article '{raw_article.title}' ({raw_article.page_id})"
                ) from error

        cleaned_count = len(cleaned_articles)
        return CleanCollectionResult(
            cleaned_articles=cleaned_articles,
            read_count=read_count,
            cleaned_count=cleaned_count,
            skipped_count=skipped_count,
            failed_count=failed_count,
        )

    def _format_final_summary(
        self,
        status: str,
        result: CleanJobResult,
        error: Exception | None = None,
    ) -> str:
        details: dict[str, Any] = {
            "Job": "clean",
            "Status": status,
            "Config": result.config_path,
            "Input": result.input_path,
            "Output": result.output_path,
            "Read": result.read_count,
            "Cleaned": result.cleaned_count,
            "Skipped": result.skipped_count,
            "Failed": result.failed_count,
            "Batch size": result.batch_size,
            "Batches": result.batch_count,
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


def build_wikipedia_clean_job() -> WikipediaCleanJob:
    """Build the Wikipedia clean job with production dependencies."""
    return WikipediaCleanJob(
        configuration_service=ConfigurationService(),
        raw_reader=RawArticleJsonlReader(),
        cleaning_service=ArticleCleaningService(),
        cleaned_writer=CleanedArticleJsonlWriter(),
    )


def main(config_path: Path | None = None) -> None:
    """Run the clean job and print a compact result summary."""
    import sys

    from vezilka_text_scraper.shared.logger import configure_logging

    resolved_config_path = config_path
    if resolved_config_path is None and len(sys.argv) > 1:
        if sys.argv[1] in {"-h", "--help"}:
            print("Usage: clean-wikipedia [config_path]")
            print(f"Default config: {WikipediaCleanJob.default_config_path}")
            return
        resolved_config_path = Path(sys.argv[1])

    configure_logging()
    result = build_wikipedia_clean_job().run(resolved_config_path)
    print(f"Cleaned {result.cleaned_count} articles to {result.output_path}")


if __name__ == "__main__":
    main()
