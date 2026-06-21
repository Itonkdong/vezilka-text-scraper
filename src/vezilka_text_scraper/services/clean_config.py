"""Configuration model for Wikipedia cleaning jobs."""

from pathlib import Path

from pydantic import BaseModel, ConfigDict, Field, field_validator

from vezilka_text_scraper.shared.constants import (
    DEFAULT_CLEAN_INPUT_PATH,
    DEFAULT_CLEAN_OUTPUT_RUN_NAME,
    DEFAULT_CONTINUE_ON_ERROR,
    DEFAULT_MIN_WORD_COUNT,
    DEFAULT_SKIP_DISAMBIGUATION_PAGES,
)


class CleanConfig(BaseModel):
    """Validated Wikipedia clean job configuration."""

    input_path: Path | None = DEFAULT_CLEAN_INPUT_PATH
    output_run_name: str | None = DEFAULT_CLEAN_OUTPUT_RUN_NAME

    min_word_count: int = Field(default=DEFAULT_MIN_WORD_COUNT, ge=0)
    skip_disambiguation_pages: bool = DEFAULT_SKIP_DISAMBIGUATION_PAGES
    continue_on_error: bool = DEFAULT_CONTINUE_ON_ERROR

    remove_templates: bool = True
    remove_references: bool = True
    remove_tables: bool = True
    remove_files: bool = True
    remove_categories: bool = True
    remove_external_links: bool = True
    remove_navigation_sections: bool = True
    normalize_whitespace: bool = True

    model_config = ConfigDict(extra="forbid")

    @field_validator("output_run_name")
    @classmethod
    def validate_output_run_name(cls, value: str | None) -> str | None:
        """Reject path-like output run names."""
        if value is None:
            return None

        normalized_value = value.strip()
        if not normalized_value:
            return None
        if Path(normalized_value).name != normalized_value:
            raise ValueError("output_run_name must be a file name, not a path")
        if not normalized_value.endswith(".jsonl"):
            return f"{normalized_value}.jsonl"
        return normalized_value
