"""Configuration model for the full Wikipedia corpus pipeline job."""

from pathlib import Path
from typing import Literal, cast

from pydantic import BaseModel, ConfigDict, model_validator

from vezilka_text_scraper.shared.constants import (
    DEFAULT_CLEAN_CONFIG_PATH,
    DEFAULT_DISPLAY_CONFIG_PATH,
    DEFAULT_DISPLAY_SOURCE,
    DEFAULT_PERSIST_CONFIG_PATH,
    DEFAULT_SCRAPE_CONFIG_PATH,
)

PipelineDisplaySource = Literal["file", "database"]


class PipelineConfig(BaseModel):
    """Validated full-pipeline orchestration configuration."""

    scrape_config_path: Path = DEFAULT_SCRAPE_CONFIG_PATH
    clean_config_path: Path = DEFAULT_CLEAN_CONFIG_PATH
    persist_config_path: Path = DEFAULT_PERSIST_CONFIG_PATH
    display_config_path: Path = DEFAULT_DISPLAY_CONFIG_PATH

    save_scraped_articles: bool = True
    save_cleaned_articles: bool = True
    persist_to_database: bool = False

    run_display: bool = True
    display_source: PipelineDisplaySource = cast(PipelineDisplaySource, DEFAULT_DISPLAY_SOURCE)

    model_config = ConfigDict(extra="forbid")

    @model_validator(mode="after")
    def validate_pipeline_goals(self) -> "PipelineConfig":
        """Ensure the pipeline has an output goal and valid display source."""
        if not self.save_cleaned_articles and not self.persist_to_database:
            raise ValueError(
                "pipeline must either save cleaned JSONL or persist cleaned articles"
            )
        if self.run_display and self.display_source == "file" and not self.save_cleaned_articles:
            raise ValueError("file display requires save_cleaned_articles=true")
        if (
            self.run_display
            and self.display_source == "database"
            and not self.persist_to_database
        ):
            raise ValueError("database display requires persist_to_database=true")
        return self
