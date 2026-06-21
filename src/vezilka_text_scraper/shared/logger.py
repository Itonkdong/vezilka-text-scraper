"""Configurable application logging."""

import json
import logging
from collections.abc import Mapping
from typing import Any

from vezilka_text_scraper.shared import env_variables
from vezilka_text_scraper.shared.constants import LOG_FORMAT_JSON
from vezilka_text_scraper.shared.exceptions import ConfigurationError

LOG_LEVELS: Mapping[str, int] = {
    "CRITICAL": logging.CRITICAL,
    "ERROR": logging.ERROR,
    "WARNING": logging.WARNING,
    "INFO": logging.INFO,
    "DEBUG": logging.DEBUG,
    "NOTSET": logging.NOTSET,
}

COLOR_CODES: Mapping[str, str] = {
    "black": "\033[30m",
    "red": "\033[31m",
    "green": "\033[32m",
    "yellow": "\033[33m",
    "blue": "\033[34m",
    "magenta": "\033[35m",
    "cyan": "\033[36m",
    "white": "\033[37m",
}
RESET_COLOR = "\033[0m"


class ColorFormatter(logging.Formatter):
    """Format log records with optional ANSI color for terminal output."""

    def __init__(self, fmt: str, use_color: bool, default_color: str) -> None:
        super().__init__(fmt=fmt)
        self._use_color = use_color
        self._default_color = default_color

    def format(self, record: logging.LogRecord) -> str:
        """Return a formatted log record."""
        message = super().format(record)
        if not self._use_color:
            return message

        color = self._resolve_record_color(record.levelno)
        if color is None:
            return message

        return f"{color}{message}{RESET_COLOR}"

    def _resolve_record_color(self, level: int) -> str | None:
        if level >= logging.CRITICAL:
            return COLOR_CODES["magenta"]
        if level >= logging.ERROR:
            return COLOR_CODES["red"]
        if level == logging.WARNING:
            return COLOR_CODES["yellow"]
        if level == logging.CRITICAL:
            return COLOR_CODES["magenta"]
        return COLOR_CODES.get(self._default_color)


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
    log_default_color: str | None = None,
) -> None:
    """Configure root logging from environment-backed logging variables."""
    active_log_level = log_level or env_variables.LOG_LEVEL
    active_log_color = env_variables.LOG_COLOR if log_color is None else log_color
    active_log_format = log_format or env_variables.LOG_FORMAT
    active_log_default_color = log_default_color or env_variables.LOG_DEFAULT_COLOR
    resolved_log_level = _resolve_log_level(active_log_level)
    _validate_color_name(active_log_default_color)

    formatter: logging.Formatter
    if active_log_format == LOG_FORMAT_JSON:
        formatter = JsonFormatter()
    else:
        formatter = ColorFormatter(
            fmt="%(asctime)s | %(levelname)-8s | %(name)s | %(message)s",
            use_color=active_log_color,
            default_color=active_log_default_color,
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


def colorize(message: str, color: str) -> str:
    """Return a colorized message when terminal colors are enabled."""
    if not env_variables.LOG_COLOR or env_variables.LOG_FORMAT == LOG_FORMAT_JSON:
        return message

    color_code = COLOR_CODES.get(color)
    if color_code is None:
        supported_colors = ", ".join(sorted(COLOR_CODES))
        raise ConfigurationError(f"Unsupported log color '{color}'. Supported: {supported_colors}.")
    return f"{color_code}{message}{RESET_COLOR}"


def _resolve_log_level(log_level: str) -> int:
    normalized_level = log_level.strip().upper()
    resolved_level = LOG_LEVELS.get(normalized_level)
    if resolved_level is None:
        supported_levels = ", ".join(sorted(LOG_LEVELS))
        raise ConfigurationError(
            f"Unsupported LOG_LEVEL '{log_level}'. Supported values: {supported_levels}."
        )
    return resolved_level


def _validate_color_name(color: str) -> None:
    if color not in COLOR_CODES:
        supported_colors = ", ".join(sorted(COLOR_CODES))
        raise ConfigurationError(
            f"Unsupported LOG_DEFAULT_COLOR '{color}'. Supported: {supported_colors}."
        )
