"""Processed article display job."""

from __future__ import annotations

from pathlib import Path
from time import perf_counter
from typing import Any

from pydantic import BaseModel, ConfigDict

from vezilka_text_scraper.adapters.article_jsonl import CleanedArticleJsonlReader
from vezilka_text_scraper.services.article_display import ArticleDisplayService
from vezilka_text_scraper.services.configuration import ConfigurationService
from vezilka_text_scraper.services.display_config import DisplayConfig
from vezilka_text_scraper.shared.constants import DEFAULT_DISPLAY_CONFIG_PATH
from vezilka_text_scraper.shared.logger import colorize, get_logger

LOGGER = get_logger(__name__)


class DisplayJobResult(BaseModel):
    """Result summary for a processed article display job."""

    model_config = ConfigDict(frozen=True)

    input_path: Path
    config_path: Path
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

    def run(self, config_path: Path | None = None) -> DisplayJobResult:
        """Run the processed article display job."""
        resolved_config_path = config_path or self.default_config_path
        started_at = perf_counter()
        input_path = Path("-")
        read_count = 0

        try:
            config = self._configuration_service.load(resolved_config_path, DisplayConfig)
            input_path = self._reader.resolve_input_path(config.input_path)
            articles = self._reader.read_articles(input_path, config.article_limit)
            read_count = len(articles)
            formatted_output = self._display_service.format_articles(articles)
            if formatted_output:
                print(formatted_output)

            result = DisplayJobResult(
                input_path=input_path,
                config_path=resolved_config_path,
                read_count=read_count,
                displayed_count=read_count,
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


def build_wikipedia_display_job() -> WikipediaDisplayJob:
    """Build the processed article display job with production dependencies."""
    return WikipediaDisplayJob(
        configuration_service=ConfigurationService(),
        reader=CleanedArticleJsonlReader(),
        display_service=ArticleDisplayService(),
    )


def main(config_path: Path | None = None) -> None:
    """Run the display job."""
    import sys

    from vezilka_text_scraper.shared.logger import configure_logging

    resolved_config_path = config_path
    if resolved_config_path is None and len(sys.argv) > 1:
        if sys.argv[1] in {"-h", "--help"}:
            print("Usage: display-wikipedia [config_path]")
            print(f"Default config: {WikipediaDisplayJob.default_config_path}")
            return
        resolved_config_path = Path(sys.argv[1])

    configure_logging()
    build_wikipedia_display_job().run(resolved_config_path)


if __name__ == "__main__":
    main()
