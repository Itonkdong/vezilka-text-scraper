"""Generic YAML configuration loading services."""

from pathlib import Path
from typing import TypeVar

import yaml
from pydantic import BaseModel, ValidationError

from vezilka_text_scraper.shared.exceptions import ServiceError

ConfigModel = TypeVar("ConfigModel", bound=BaseModel)


class ConfigurationService:
    """Load YAML configuration files into typed Pydantic models."""

    def load(self, config_path: Path, config_model: type[ConfigModel]) -> ConfigModel:
        """Load a YAML config file into the provided Pydantic model.

        Raises:
            ServiceError: If the file cannot be read, parsed, or validated.
        """
        if not config_path.exists():
            raise ServiceError(f"Configuration file does not exist: {config_path}")

        try:
            loaded_config = yaml.safe_load(config_path.read_text(encoding="utf-8"))
        except yaml.YAMLError as error:
            raise ServiceError(f"Invalid YAML configuration: {config_path}") from error
        except OSError as error:
            raise ServiceError(f"Could not read configuration: {config_path}") from error

        if loaded_config is None:
            loaded_config = {}
        if not isinstance(loaded_config, dict):
            raise ServiceError("Configuration YAML root must be a mapping")

        try:
            return config_model(**loaded_config)
        except ValidationError as error:
            raise ServiceError(
                f"Invalid configuration: {self._format_validation_error(error)}"
            ) from error

    def _format_validation_error(self, error: ValidationError) -> str:
        messages: list[str] = []
        for detail in error.errors():
            location = ".".join(str(part) for part in detail.get("loc", ()) if part)
            message = str(detail.get("msg", "validation failed"))
            message = message.removeprefix("Value error, ")
            if location:
                messages.append(f"{location}: {message}")
            else:
                messages.append(message)
        return "; ".join(messages)
