"""Configuration model for database initialization jobs."""

from pydantic import BaseModel, ConfigDict, Field

from vezilka_text_scraper.services.persist_config import DatabaseConfig


class InitDatabaseConfig(BaseModel):
    """Validated init-database job configuration."""

    database: DatabaseConfig = Field(default_factory=DatabaseConfig)

    model_config = ConfigDict(extra="forbid")
