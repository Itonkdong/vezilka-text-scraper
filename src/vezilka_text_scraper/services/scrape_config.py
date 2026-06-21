"""Configuration model for Wikipedia scraping jobs."""

from pathlib import Path

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

from vezilka_text_scraper.shared.constants import (
    DEFAULT_CATEGORY_MAX_DEPTH,
    DEFAULT_CONTINUE_ON_ERROR,
    DEFAULT_INCLUDE_REDIRECTS,
    DEFAULT_PER_CATEGORY_ARTICLE_LIMIT,
    DEFAULT_RECURSIVE_CATEGORY_CRAWL,
    DEFAULT_REQUEST_DELAY_SECONDS,
    DEFAULT_SCRAPE_BATCH_SIZE,
    DEFAULT_TOTAL_ARTICLE_LIMIT,
    DEFAULT_WIKIPEDIA_NAMESPACE,
    SUITABLE_WIKIPEDIA_CATEGORIES,
)


class ScrapeConfig(BaseModel):
    """Validated Wikipedia scrape job configuration."""

    categories: list[str]
    recursive: bool = DEFAULT_RECURSIVE_CATEGORY_CRAWL
    max_depth: int = Field(default=DEFAULT_CATEGORY_MAX_DEPTH, ge=0)
    total_article_limit: int | None = Field(default=DEFAULT_TOTAL_ARTICLE_LIMIT, gt=0)
    per_category_article_limit: int | None = Field(
        default=DEFAULT_PER_CATEGORY_ARTICLE_LIMIT,
        gt=0,
    )
    include_redirects: bool = DEFAULT_INCLUDE_REDIRECTS
    namespace: int = Field(default=DEFAULT_WIKIPEDIA_NAMESPACE, ge=0)
    request_delay_seconds: float = Field(default=DEFAULT_REQUEST_DELAY_SECONDS, ge=0)
    continue_on_error: bool = DEFAULT_CONTINUE_ON_ERROR
    batch_size: int = Field(default=DEFAULT_SCRAPE_BATCH_SIZE, ge=1)
    output_run_name: str | None = None

    model_config = ConfigDict(extra="forbid")

    @field_validator("categories", mode="before")
    @classmethod
    def expand_all_categories(cls, value: object) -> object:
        """Allow `categories: all` as shorthand for every supported category."""
        if isinstance(value, str) and value.strip().casefold() == "all":
            return sorted(SUITABLE_WIKIPEDIA_CATEGORIES)
        if isinstance(value, list) and any(
            isinstance(category, str) and category.strip().casefold() == "all"
            for category in value
        ):
            return sorted(SUITABLE_WIKIPEDIA_CATEGORIES)
        return value

    @field_validator("categories")
    @classmethod
    def validate_categories(cls, value: list[str]) -> list[str]:
        """Return normalized categories after validating the approved category set."""
        normalized_categories = [category.strip() for category in value if category.strip()]
        if not normalized_categories:
            raise ValueError("categories must include at least one category")

        unsupported_categories = sorted(
            {
                category
                for category in normalized_categories
                if category not in SUITABLE_WIKIPEDIA_CATEGORIES
            }
        )
        if unsupported_categories:
            supported_categories = ", ".join(sorted(SUITABLE_WIKIPEDIA_CATEGORIES))
            raise ValueError(
                "categories must be selected from the supported category list. "
                f"Unsupported: {', '.join(unsupported_categories)}. "
                f"Supported: {supported_categories}"
            )

        return normalized_categories

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

    @model_validator(mode="after")
    def validate_recursion_depth(self) -> "ScrapeConfig":
        """Keep non-recursive crawls pinned to direct category members."""
        if not self.recursive and self.max_depth != 0:
            self.max_depth = 0
        return self
