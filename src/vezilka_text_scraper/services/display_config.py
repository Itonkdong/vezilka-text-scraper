"""Configuration model for processed article display jobs."""

from pathlib import Path
from typing import Literal, cast

from pydantic import BaseModel, ConfigDict, Field, field_validator

from vezilka_text_scraper.shared.constants import (
    DEFAULT_DISPLAY_ARTICLE_LIMIT,
    DEFAULT_DISPLAY_INPUT_PATH,
    DEFAULT_DISPLAY_SOURCE,
)

DisplaySource = Literal["file", "database"]


class DisplayConfig(BaseModel):
    """Validated processed article display job configuration."""

    source: DisplaySource = cast(DisplaySource, DEFAULT_DISPLAY_SOURCE)
    input_path: Path | None = DEFAULT_DISPLAY_INPUT_PATH
    article_limit: int = Field(default=DEFAULT_DISPLAY_ARTICLE_LIMIT, gt=0)

    model_config = ConfigDict(extra="forbid")

    @field_validator("source", mode="before")
    @classmethod
    def normalize_source(cls, value: object) -> object:
        """Normalize display source aliases."""
        if isinstance(value, str):
            normalized_value = value.strip().lower()
            if normalized_value in {"db", "database"}:
                return "database"
            if normalized_value in {"file", "files", "jsonl"}:
                return "file"
            return normalized_value
        return value
