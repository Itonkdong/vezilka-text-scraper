"""Article models used across pipeline jobs."""

from pydantic import BaseModel, ConfigDict, Field


class RawArticleInput(BaseModel):
    """Raw article record read from scraper JSONL output."""

    model_config = ConfigDict(frozen=True)

    page_id: int
    title: str
    url: str
    language: str
    categories: list[str]
    revision_id: int
    last_modified: str
    scraped_at: str
    source_categories: list[str]
    raw_wikitext: str


class CleanedSection(BaseModel):
    """Cleaned article section."""

    model_config = ConfigDict(frozen=True)

    heading: str
    content: str
    word_count: int = Field(ge=0)
    char_count: int = Field(ge=0)
    position: int = Field(ge=0)


class CleanedArticle(BaseModel):
    """Cleaned article record written to processed JSONL output."""

    model_config = ConfigDict(frozen=True)

    page_id: int
    title: str
    url: str
    language: str
    categories: list[str]
    revision_id: int
    last_modified: str
    scraped_at: str
    cleaned_at: str
    source_categories: list[str]
    clean_text: str
    word_count: int = Field(ge=0)
    char_count: int = Field(ge=0)
    section_count: int = Field(ge=0)
    sections: list[CleanedSection]
