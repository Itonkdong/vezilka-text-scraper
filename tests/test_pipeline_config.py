from pathlib import Path

import pytest

from vezilka_text_scraper.services.configuration import ConfigurationService
from vezilka_text_scraper.services.pipeline_config import PipelineConfig
from vezilka_text_scraper.shared.constants import (
    DEFAULT_CLEAN_CONFIG_PATH,
    DEFAULT_DISPLAY_CONFIG_PATH,
    DEFAULT_PERSIST_CONFIG_PATH,
    DEFAULT_SCRAPE_CONFIG_PATH,
)
from vezilka_text_scraper.shared.exceptions import ServiceError


def test_load_full_pipeline_config(tmp_path: Path) -> None:
    config_path = tmp_path / "pipeline.yaml"
    config_path.write_text(
        """
scrape_config_path: custom/scrape.yaml
clean_config_path: custom/clean.yaml
persist_config_path: custom/persist.yaml
display_config_path: custom/display.yaml
save_scraped_articles: false
save_cleaned_articles: false
persist_to_database: true
run_display: true
display_source: database
""",
        encoding="utf-8",
    )

    config = ConfigurationService().load(config_path, PipelineConfig)

    assert config.scrape_config_path == Path("custom/scrape.yaml")
    assert config.clean_config_path == Path("custom/clean.yaml")
    assert config.persist_config_path == Path("custom/persist.yaml")
    assert config.display_config_path == Path("custom/display.yaml")
    assert config.save_scraped_articles is False
    assert config.save_cleaned_articles is False
    assert config.persist_to_database is True
    assert config.run_display is True
    assert config.display_source == "database"


def test_load_partial_pipeline_config_uses_defaults(tmp_path: Path) -> None:
    config_path = tmp_path / "pipeline.yaml"
    config_path.write_text("", encoding="utf-8")

    config = ConfigurationService().load(config_path, PipelineConfig)

    assert config.scrape_config_path == DEFAULT_SCRAPE_CONFIG_PATH
    assert config.clean_config_path == DEFAULT_CLEAN_CONFIG_PATH
    assert config.persist_config_path == DEFAULT_PERSIST_CONFIG_PATH
    assert config.display_config_path == DEFAULT_DISPLAY_CONFIG_PATH
    assert config.save_scraped_articles is True
    assert config.save_cleaned_articles is True
    assert config.persist_to_database is False
    assert config.run_display is True
    assert config.display_source == "file"


@pytest.mark.parametrize(
    "config_text",
    [
        "save_cleaned_articles: false\npersist_to_database: false\n",
        (
            "save_cleaned_articles: false\npersist_to_database: true\n"
            "run_display: true\ndisplay_source: file\n"
        ),
        (
            "save_cleaned_articles: true\npersist_to_database: false\n"
            "run_display: true\ndisplay_source: database\n"
        ),
        "display_source: api\n",
        "unknown_field: true\n",
    ],
)
def test_load_invalid_pipeline_config_raises_service_error(
    tmp_path: Path,
    config_text: str,
) -> None:
    config_path = tmp_path / "pipeline.yaml"
    config_path.write_text(config_text, encoding="utf-8")

    with pytest.raises(ServiceError):
        ConfigurationService().load(config_path, PipelineConfig)
