"""Database schema initialization job."""

from __future__ import annotations

from pathlib import Path
from time import perf_counter
from typing import Any

from pydantic import BaseModel, ConfigDict, Field

from vezilka_text_scraper.adapters.database import ArticleDatabaseAdapter
from vezilka_text_scraper.services.configuration import ConfigurationService
from vezilka_text_scraper.services.init_database_config import InitDatabaseConfig
from vezilka_text_scraper.shared.constants import DEFAULT_INIT_DATABASE_CONFIG_PATH
from vezilka_text_scraper.shared.logger import colorize, get_logger

LOGGER = get_logger(__name__)


class InitDatabaseJobResult(BaseModel):
    """Result summary for database initialization."""

    model_config = ConfigDict(frozen=True)

    config_path: Path
    database_type: str
    database_url: str
    created_schema: bool
    existing_table_count: int = Field(ge=0)
    created_table_count: int = Field(ge=0)
    added_column_count: int = Field(ge=0)
    duration_seconds: float


class InitDatabaseJob:
    """Initialize the configured database schema for persisted corpus records."""

    default_config_path = DEFAULT_INIT_DATABASE_CONFIG_PATH

    def __init__(self, configuration_service: ConfigurationService) -> None:
        self._configuration_service = configuration_service

    def run(self, config_path: Path | None = None) -> InitDatabaseJobResult:
        """Run the database initialization job."""
        resolved_config_path = config_path or self.default_config_path
        started_at = perf_counter()
        database_type = "-"
        database_url = "-"

        try:
            config = self._configuration_service.load(resolved_config_path, InitDatabaseConfig)
            database_type = config.database.type
            database_adapter = ArticleDatabaseAdapter(config.database)
            database_url = database_adapter.mask_database_url()

            LOGGER.info(f"Starting database initialization for {database_url}")
            initialized = database_adapter.initialize_schema()
            result = InitDatabaseJobResult(
                config_path=resolved_config_path,
                database_type=database_type,
                database_url=database_url,
                created_schema=initialized.created_schema,
                existing_table_count=initialized.existing_table_count,
                created_table_count=initialized.created_table_count,
                added_column_count=initialized.added_column_count,
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
            result = InitDatabaseJobResult(
                config_path=resolved_config_path,
                database_type=database_type,
                database_url=database_url,
                created_schema=False,
                existing_table_count=0,
                created_table_count=0,
                added_column_count=0,
                duration_seconds=perf_counter() - started_at,
            )
            LOGGER.error(
                colorize(
                    self._format_final_summary(
                        status="FAILED",
                        result=result,
                        error=error,
                    ),
                    "red",
                )
            )
            raise

    def _format_final_summary(
        self,
        status: str,
        result: InitDatabaseJobResult,
        error: Exception | None = None,
    ) -> str:
        details: dict[str, Any] = {
            "Job": "init-database",
            "Status": status,
            "Config": result.config_path,
            "Database": result.database_type,
            "DB URL": result.database_url,
            "Schema made": result.created_schema,
            "Existing": result.existing_table_count,
            "Created": result.created_table_count,
            "Columns": result.added_column_count,
            "Duration": f"{result.duration_seconds:.2f}s",
        }
        if error is not None:
            details["Reason"] = str(error)

        width = 80
        title = f" {status} JOB SUMMARY "
        border = f"+{title.center(width - 2, '=')}+"
        lines = ["", border]
        for key, value in details.items():
            lines.append(f"| {key:<14}: {str(value):<{width - 19}} |")
        lines.append(f"+{'=' * (width - 2)}+")
        return "\n".join(lines)


def build_init_database_job() -> InitDatabaseJob:
    """Build the init-database job with production dependencies."""
    return InitDatabaseJob(configuration_service=ConfigurationService())


def main(config_path: Path | None = None) -> None:
    """Run the database initialization job."""
    import sys

    from vezilka_text_scraper.shared.logger import configure_logging

    resolved_config_path = config_path
    if resolved_config_path is None and len(sys.argv) > 1:
        if sys.argv[1] in {"-h", "--help"}:
            print("Usage: init-database [config_path]")
            print(f"Default config: {InitDatabaseJob.default_config_path}")
            return
        resolved_config_path = Path(sys.argv[1])

    configure_logging()
    result = build_init_database_job().run(resolved_config_path)
    print(
        f"Initialized database with {result.created_table_count} created tables "
        f"({result.existing_table_count} already existed)"
    )


if __name__ == "__main__":
    main()
