"""Configuration model for database persistence jobs."""

import re
from pathlib import Path
from typing import Literal, cast

from pydantic import BaseModel, ConfigDict, Field, field_validator

from vezilka_text_scraper.shared import env_variables
from vezilka_text_scraper.shared.constants import (
    DEFAULT_DATABASE_TYPE,
    DEFAULT_PERSIST_ARTICLE_LIMIT,
    DEFAULT_PERSIST_BATCH_SIZE,
    DEFAULT_PERSIST_INPUT_PATH,
)

DatabaseType = Literal["sqlite", "postgresql"]
SCHEMA_NAME_PATTERN = re.compile(r"^[A-Za-z_][A-Za-z0-9_]*$")


class DatabaseConfig(BaseModel):
    """Validated database target configuration."""

    type: DatabaseType = cast(DatabaseType, DEFAULT_DATABASE_TYPE)

    model_config = ConfigDict(extra="forbid")

    @property
    def url(self) -> str:
        """Return the SQLAlchemy database URL built from shared env variables."""
        if self.type == "sqlite":
            return f"sqlite:///{env_variables.SQLITE_DATABASE_PATH}"
        return (
            "postgresql+psycopg://"
            f"{env_variables.POSTGRES_USER}:{env_variables.POSTGRES_PASSWORD}"
            f"@{env_variables.POSTGRES_HOST}:{env_variables.POSTGRES_PORT}"
            f"/{env_variables.POSTGRES_DATABASE}"
        )

    @property
    def schema_name(self) -> str | None:
        """Return the configured database schema from shared env variables."""
        if self.type == "postgresql":
            return env_variables.POSTGRES_SCHEMA
        return None

    @field_validator("type", mode="before")
    @classmethod
    def normalize_database_type(cls, value: object) -> object:
        """Normalize postgres aliases to the SQLAlchemy dialect name."""
        if isinstance(value, str) and value.strip().lower() in {"postgres", "postgresql"}:
            return "postgresql"
        if isinstance(value, str):
            return value.strip().lower()
        return value

    @field_validator("type")
    @classmethod
    def validate_database_env(cls, value: DatabaseType) -> DatabaseType:
        """Validate environment-backed database settings for the selected type."""
        if value == "postgresql" and not SCHEMA_NAME_PATTERN.fullmatch(
            env_variables.POSTGRES_SCHEMA
        ):
            raise ValueError("POSTGRES_SCHEMA must be a simple SQL identifier")
        return value


class PersistConfig(BaseModel):
    """Validated persist job configuration."""

    input_path: Path | None = DEFAULT_PERSIST_INPUT_PATH
    article_limit: int | None = Field(default=DEFAULT_PERSIST_ARTICLE_LIMIT, ge=1)
    batch_size: int = Field(default=DEFAULT_PERSIST_BATCH_SIZE, ge=1)
    database: DatabaseConfig = Field(default_factory=DatabaseConfig)

    model_config = ConfigDict(extra="forbid")
