import logging

import pytest

from vezilka_text_scraper.shared import env_variables
from vezilka_text_scraper.shared.exceptions import ConfigurationError
from vezilka_text_scraper.shared.logger import colorize, configure_logging


def test_configure_logging_uses_env_level() -> None:
    configure_logging(log_level="DEBUG", log_color=False)

    assert logging.getLogger().level == logging.DEBUG


def test_configure_logging_rejects_invalid_level() -> None:
    with pytest.raises(ConfigurationError):
        configure_logging(log_level="LOUD", log_color=False)


def test_configure_logging_rejects_invalid_default_color() -> None:
    with pytest.raises(ConfigurationError):
        configure_logging(log_default_color="chartreuse")


def test_colorize_uses_requested_color(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(env_variables, "LOG_COLOR", True)
    monkeypatch.setattr(env_variables, "LOG_FORMAT", "human")

    message = colorize("summary", "green")

    assert message.startswith("\033[32m")
    assert message.endswith("\033[0m")
