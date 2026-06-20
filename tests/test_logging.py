import logging

import pytest

from vezilka_text_scraper.shared.exceptions import ConfigurationError
from vezilka_text_scraper.shared.logger import configure_logging


def test_configure_logging_uses_env_level() -> None:
    configure_logging(log_level="DEBUG", log_color=False)

    assert logging.getLogger().level == logging.DEBUG


def test_configure_logging_rejects_invalid_level() -> None:
    with pytest.raises(ConfigurationError):
        configure_logging(log_level="LOUD", log_color=False)
