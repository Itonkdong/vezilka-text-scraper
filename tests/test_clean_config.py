from pathlib import Path

import pytest

from vezilka_text_scraper.services.clean_config import CleanConfig
from vezilka_text_scraper.services.configuration import ConfigurationService
from vezilka_text_scraper.shared.constants import (
    DEFAULT_CLEAN_BATCH_SIZE,
    DEFAULT_LOG_SKIPPED_ARTICLES,
    DEFAULT_MIN_SECTION_WORD_COUNT,
    DEFAULT_MIN_WORD_COUNT,
    DEFAULT_REMOVE_CODE_SECTIONS,
    DEFAULT_SKIP_DISAMBIGUATION_PAGES,
)
from vezilka_text_scraper.shared.exceptions import ServiceError


def test_load_full_clean_config(tmp_path: Path) -> None:
    config_path = tmp_path / "clean.yaml"
    config_path.write_text(
        """
input_path: data/raw/sample.jsonl
output_run_name: clean_test
batch_size: 8
min_word_count: 10
min_section_word_count: 4
skip_disambiguation_pages: false
continue_on_error: false
log_skipped_articles: false
remove_templates: false
remove_references: false
remove_tables: false
remove_files: false
remove_categories: false
remove_external_links: false
remove_navigation_sections: false
remove_code_sections: false
normalize_whitespace: false
""",
        encoding="utf-8",
    )

    config = ConfigurationService().load(config_path, CleanConfig)

    assert config.input_path == Path("data/raw/sample.jsonl")
    assert config.output_run_name == "clean_test.jsonl"
    assert config.batch_size == 8
    assert config.min_word_count == 10
    assert config.min_section_word_count == 4
    assert config.skip_disambiguation_pages is False
    assert config.continue_on_error is False
    assert config.log_skipped_articles is False
    assert config.remove_templates is False
    assert config.remove_code_sections is False
    assert config.normalize_whitespace is False


def test_load_partial_clean_config_uses_defaults(tmp_path: Path) -> None:
    config_path = tmp_path / "clean.yaml"
    config_path.write_text("", encoding="utf-8")

    config = ConfigurationService().load(config_path, CleanConfig)

    assert config.input_path is None
    assert config.output_run_name is None
    assert config.batch_size == DEFAULT_CLEAN_BATCH_SIZE
    assert config.min_word_count == DEFAULT_MIN_WORD_COUNT
    assert config.min_section_word_count == DEFAULT_MIN_SECTION_WORD_COUNT
    assert config.skip_disambiguation_pages is DEFAULT_SKIP_DISAMBIGUATION_PAGES
    assert config.continue_on_error is True
    assert config.log_skipped_articles is DEFAULT_LOG_SKIPPED_ARTICLES
    assert config.remove_code_sections is DEFAULT_REMOVE_CODE_SECTIONS


@pytest.mark.parametrize(
    "config_text",
    [
        "min_word_count: -1\n",
        "min_section_word_count: -1\n",
        "batch_size: 0\n",
        "output_run_name: nested/name\n",
        "unknown_field: true\n",
    ],
)
def test_load_invalid_clean_config_raises_service_error(
    tmp_path: Path,
    config_text: str,
) -> None:
    config_path = tmp_path / "clean.yaml"
    config_path.write_text(config_text, encoding="utf-8")

    with pytest.raises(ServiceError):
        ConfigurationService().load(config_path, CleanConfig)
