from pathlib import Path

import pytest

from vezilka_text_scraper.services.configuration import ConfigurationService
from vezilka_text_scraper.services.scrape_config import ScrapeConfig
from vezilka_text_scraper.shared.constants import (
    DEFAULT_CATEGORY_MAX_DEPTH,
    DEFAULT_CONTINUE_ON_ERROR,
    DEFAULT_RECURSIVE_CATEGORY_CRAWL,
    DEFAULT_SCRAPE_BATCH_SIZE,
)
from vezilka_text_scraper.shared.exceptions import ServiceError


def test_load_full_scrape_config(tmp_path: Path) -> None:
    config_path = tmp_path / "scrape.yaml"
    config_path.write_text(
        """
categories:
  - Географија
recursive: false
max_depth: 4
total_article_limit: 10
per_category_article_limit: 3
include_redirects: true
namespace: 0
request_delay_seconds: 0
continue_on_error: false
batch_size: 7
output_run_name: sample_run
""",
        encoding="utf-8",
    )

    config = ConfigurationService().load(config_path, ScrapeConfig)

    assert config.categories == ["Географија"]
    assert config.recursive is False
    assert config.max_depth == 0
    assert config.total_article_limit == 10
    assert config.per_category_article_limit == 3
    assert config.include_redirects is True
    assert config.continue_on_error is False
    assert config.batch_size == 7
    assert config.output_run_name == "sample_run.jsonl"


def test_load_partial_scrape_config_uses_defaults(tmp_path: Path) -> None:
    config_path = tmp_path / "scrape.yaml"
    config_path.write_text("categories:\n  - Наука\n", encoding="utf-8")

    config = ConfigurationService().load(config_path, ScrapeConfig)

    assert config.categories == ["Наука"]
    assert config.recursive is DEFAULT_RECURSIVE_CATEGORY_CRAWL
    assert config.max_depth == DEFAULT_CATEGORY_MAX_DEPTH
    assert config.continue_on_error is DEFAULT_CONTINUE_ON_ERROR
    assert config.batch_size == DEFAULT_SCRAPE_BATCH_SIZE


@pytest.mark.parametrize(
    "config_text",
    [
        "categories: []\n",
        "categories:\n  - Неподдржана\n",
        "categories:\n  - Географија\nmax_depth: -1\n",
        "categories:\n  - Географија\ntotal_article_limit: 0\n",
        "categories:\n  - Географија\nrequest_delay_seconds: -0.1\n",
        "categories:\n  - Географија\nbatch_size: 0\n",
        "categories:\n  - Географија\noutput_run_name: nested/name\n",
    ],
)
def test_load_invalid_scrape_config_raises_service_error(
    tmp_path: Path,
    config_text: str,
) -> None:
    config_path = tmp_path / "scrape.yaml"
    config_path.write_text(config_text, encoding="utf-8")

    with pytest.raises(ServiceError):
        ConfigurationService().load(config_path, ScrapeConfig)
