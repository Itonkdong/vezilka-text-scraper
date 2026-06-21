from pathlib import Path

import pytest

from vezilka_text_scraper.services.configuration import ConfigurationService
from vezilka_text_scraper.services.display_config import DisplayConfig
from vezilka_text_scraper.shared.constants import (
    DEFAULT_DISPLAY_ARTICLE_LIMIT,
    DEFAULT_DISPLAY_RANDOM_SAMPLE,
    DEFAULT_DISPLAY_SOURCE,
)
from vezilka_text_scraper.shared.exceptions import ServiceError


def test_load_full_display_config(tmp_path: Path) -> None:
    config_path = tmp_path / "display.yaml"
    config_path.write_text(
        """
input_path: data/processed/sample.jsonl
article_limit: 5
random_sample: true
source: postgresql
""",
        encoding="utf-8",
    )

    config = ConfigurationService().load(config_path, DisplayConfig)

    assert config.input_path == Path("data/processed/sample.jsonl")
    assert config.article_limit == 5
    assert config.random_sample is True
    assert config.source == "postgresql"


def test_load_partial_display_config_uses_defaults(tmp_path: Path) -> None:
    config_path = tmp_path / "display.yaml"
    config_path.write_text("", encoding="utf-8")

    config = ConfigurationService().load(config_path, DisplayConfig)

    assert config.input_path is None
    assert config.article_limit == DEFAULT_DISPLAY_ARTICLE_LIMIT
    assert config.random_sample is DEFAULT_DISPLAY_RANDOM_SAMPLE
    assert config.source == DEFAULT_DISPLAY_SOURCE


def test_load_display_config_normalizes_source_alias(tmp_path: Path) -> None:
    config_path = tmp_path / "display.yaml"
    config_path.write_text("source: postgres\n", encoding="utf-8")

    config = ConfigurationService().load(config_path, DisplayConfig)

    assert config.source == "postgresql"


@pytest.mark.parametrize(
    "config_text",
    [
        "article_limit: 0\n",
        "source: api\n",
        "source: database\n",
        "source: db\n",
        "unknown_field: true\n",
    ],
)
def test_load_invalid_display_config_raises_service_error(
    tmp_path: Path,
    config_text: str,
) -> None:
    config_path = tmp_path / "display.yaml"
    config_path.write_text(config_text, encoding="utf-8")

    with pytest.raises(ServiceError):
        ConfigurationService().load(config_path, DisplayConfig)
