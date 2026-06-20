"""Configurable application logging."""

import json
import logging
from collections.abc import Mapping
from typing import Any

from vezilka_text_scraper.shared.constants import LOG_FORMAT_JSON
from vezilka_text_scraper.shared import env_variables
from vezilka_text_scraper.shared.exceptions import ConfigurationError

LOG_LEVELS: Mapping[str, int] = {
    "CRITICAL": logging.CRITICAL,
    "ERROR": logging.ERROR,
    "WARNING": logging.WARNING,
    "INFO": logging.INFO,
    "DEBUG": logging.DEBUG,
    "NOTSET": logging.NOTSET,
}

LEVEL_COLORS: Mapping[int, str] = {
    logging.DEBUG: "\033[36m",
    logging.INFO: "\033[32m",
    logging.WARNING: "\033[33m",
    logging.ERROR: "\033[31m",
    logging.CRITICAL: "\033[35m",
}
RESET_COLOR = "\033[0m"


class ColorFormatter(logging.Formatter):
    """Format log records with optional ANSI color for terminal output."""

    def __init__(self, fmt: str, use_color: bool) -> None:
        super().__init__(fmt=fmt)
        self._use_color = use_color

    def format(self, record: logging.LogRecord) -> str:
        """Return a formatted log record."""
        message = super().format(record)
        if not self._use_color:
            return message

        color = LEVEL_COLORS.get(record.levelno)
        if color is None:
            return message

        return f"{color}{message}{RESET_COLOR}"


class JsonFormatter(logging.Formatter):
    """Format log records as single-line JSON."""

    def format(self, record: logging.LogRecord) -> str:
        """Return a JSON log record."""
        payload: dict[str, Any] = {
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
            "timestamp": self.formatTime(record, self.datefmt),
        }
        if record.exc_info is not None:
            payload["exception"] = self.formatException(record.exc_info)
        return json.dumps(payload, ensure_ascii=False)


def configure_logging(
    log_level: str | None = None,
    log_color: bool | None = None,
    log_format: str | None = None,
) -> None:
    """Configure root logging from environment-backed logging variables."""
    active_log_level = log_level or env_variables.LOG_LEVEL
    active_log_color = env_variables.LOG_COLOR if log_color is None else log_color
    active_log_format = log_format or env_variables.LOG_FORMAT
    resolved_log_level = _resolve_log_level(active_log_level)

    formatter: logging.Formatter
    if active_log_format == LOG_FORMAT_JSON:
        formatter = JsonFormatter()
    else:
        formatter = ColorFormatter(
            fmt="%(asctime)s | %(levelname)-8s | %(name)s | %(message)s",
            use_color=active_log_color,
        )

    handler = logging.StreamHandler()
    handler.setFormatter(formatter)

    root_logger = logging.getLogger()
    root_logger.handlers.clear()
    root_logger.addHandler(handler)
    root_logger.setLevel(resolved_log_level)


def get_logger(name: str) -> logging.Logger:
    """Return a logger for the given module or component name."""
    return logging.getLogger(name)


def _resolve_log_level(log_level: str) -> int:
    normalized_level = log_level.strip().upper()
    resolved_level = LOG_LEVELS.get(normalized_level)
    if resolved_level is None:
        supported_levels = ", ".join(sorted(LOG_LEVELS))
        raise ConfigurationError(
            f"Unsupported LOG_LEVEL '{log_level}'. Supported values: {supported_levels}."
        )
    return resolved_level
