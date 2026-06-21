"""Configuration model for processed article display jobs."""

from pathlib import Path

from pydantic import BaseModel, ConfigDict, Field

from vezilka_text_scraper.shared.constants import (
    DEFAULT_DISPLAY_ARTICLE_LIMIT,
    DEFAULT_DISPLAY_INPUT_PATH,
)


class DisplayConfig(BaseModel):
    """Validated processed article display job configuration."""

    input_path: Path | None = DEFAULT_DISPLAY_INPUT_PATH
    article_limit: int = Field(default=DEFAULT_DISPLAY_ARTICLE_LIMIT, gt=0)

    model_config = ConfigDict(extra="forbid")
