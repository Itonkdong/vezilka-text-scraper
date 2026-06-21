import json
import logging
from pathlib import Path

import pytest

from vezilka_text_scraper.adapters.article_jsonl import (
    CleanedArticleJsonlWriter,
    RawArticleJsonlReader,
)
from vezilka_text_scraper.jobs.clean import WikipediaCleanJob
from vezilka_text_scraper.models.article import RawArticleInput
from vezilka_text_scraper.services.article_cleaning import (
    ArticleCleaningService,
    CleanedArticleCandidate,
)
from vezilka_text_scraper.services.clean_config import CleanConfig
from vezilka_text_scraper.services.configuration import ConfigurationService
from vezilka_text_scraper.shared.exceptions import ServiceError


class FailingArticleCleaningService(ArticleCleaningService):
    def clean_article(
        self,
        article: RawArticleInput,
        config: CleanConfig,
        cleaned_at: str,
    ) -> CleanedArticleCandidate:
        raise ServiceError("forced cleaning failure")


def _raw_record(page_id: int, title: str, raw_wikitext: str) -> dict[str, object]:
    return {
        "page_id": page_id,
        "title": title,
        "url": f"https://mk.wikipedia.org/wiki/{title}",
        "language": "mk",
        "categories": ["Категорија:Географија"],
        "revision_id": 10 + page_id,
        "last_modified": "2026-01-01T00:00:00Z",
        "scraped_at": "2026-06-21T00:00:00+00:00",
        "source_categories": ["Географија"],
        "raw_wikitext": raw_wikitext,
    }


def test_clean_job_writes_processed_jsonl_and_applies_filters(tmp_path: Path) -> None:
    raw_dir = tmp_path / "raw"
    processed_dir = tmp_path / "processed"
    raw_dir.mkdir()
    input_path = raw_dir / "raw.jsonl"
    input_path.write_text(
        "\n".join(
            [
                json.dumps(
                    _raw_record(
                        1,
                        "Географија",
                        "Географија е наука со доволно зборови за да помине филтер.",
                    ),
                    ensure_ascii=False,
                ),
                json.dumps(_raw_record(2, "Кратко", "Кратко."), ensure_ascii=False),
            ]
        ),
        encoding="utf-8",
    )
    config_path = tmp_path / "clean.yaml"
    config_path.write_text(
        f"""
input_path: {input_path}
output_run_name: clean_test
batch_size: 1
min_word_count: 5
skip_disambiguation_pages: true
continue_on_error: true
""",
        encoding="utf-8",
    )
    job = WikipediaCleanJob(
        configuration_service=ConfigurationService(),
        raw_reader=RawArticleJsonlReader(raw_dir),
        cleaning_service=ArticleCleaningService(),
        cleaned_writer=CleanedArticleJsonlWriter(processed_dir),
    )

    result = job.run(config_path)

    assert result.read_count == 2
    assert result.cleaned_count == 1
    assert result.skipped_count == 1
    assert result.failed_count == 0
    assert result.batch_size == 1
    assert result.batch_count == 2
    records = [
        json.loads(line)
        for line in result.output_path.read_text(encoding="utf-8").splitlines()
    ]
    assert records[0]["title"] == "Географија"


def test_clean_job_logs_skip_reasons(
    tmp_path: Path,
    caplog: pytest.LogCaptureFixture,
) -> None:
    raw_dir = tmp_path / "raw"
    processed_dir = tmp_path / "processed"
    raw_dir.mkdir()
    input_path = raw_dir / "raw.jsonl"
    input_path.write_text(
        json.dumps(_raw_record(1, "Кратко", "Кратко."), ensure_ascii=False),
        encoding="utf-8",
    )
    config_path = tmp_path / "clean.yaml"
    config_path.write_text(
        f"""
input_path: {input_path}
output_run_name: clean_test
min_word_count: 5
min_section_word_count: 0
continue_on_error: true
""",
        encoding="utf-8",
    )
    job = WikipediaCleanJob(
        configuration_service=ConfigurationService(),
        raw_reader=RawArticleJsonlReader(raw_dir),
        cleaning_service=ArticleCleaningService(),
        cleaned_writer=CleanedArticleJsonlWriter(processed_dir),
    )

    with caplog.at_level(logging.INFO, logger="vezilka_text_scraper.jobs.clean"):
        result = job.run(config_path)

    assert result.skipped_count == 1
    assert "Skipping cleaned article 'Кратко' (1)" in caplog.text
    assert "word count 2 is below minimum 5" in caplog.text


def test_clean_job_can_suppress_skip_reason_logs(
    tmp_path: Path,
    caplog: pytest.LogCaptureFixture,
) -> None:
    raw_dir = tmp_path / "raw"
    processed_dir = tmp_path / "processed"
    raw_dir.mkdir()
    input_path = raw_dir / "raw.jsonl"
    input_path.write_text(
        json.dumps(_raw_record(1, "Кратко", "Кратко."), ensure_ascii=False),
        encoding="utf-8",
    )
    config_path = tmp_path / "clean.yaml"
    config_path.write_text(
        f"""
input_path: {input_path}
output_run_name: clean_test
min_word_count: 5
min_section_word_count: 0
continue_on_error: true
log_skipped_articles: false
""",
        encoding="utf-8",
    )
    job = WikipediaCleanJob(
        configuration_service=ConfigurationService(),
        raw_reader=RawArticleJsonlReader(raw_dir),
        cleaning_service=ArticleCleaningService(),
        cleaned_writer=CleanedArticleJsonlWriter(processed_dir),
    )

    with caplog.at_level(logging.INFO, logger="vezilka_text_scraper.jobs.clean"):
        result = job.run(config_path)

    assert result.skipped_count == 1
    assert "Skipping cleaned article 'Кратко' (1)" not in caplog.text


def test_clean_job_always_logs_failed_articles(
    tmp_path: Path,
    caplog: pytest.LogCaptureFixture,
) -> None:
    raw_dir = tmp_path / "raw"
    processed_dir = tmp_path / "processed"
    raw_dir.mkdir()
    input_path = raw_dir / "raw.jsonl"
    input_path.write_text(
        json.dumps(_raw_record(1, "Географија", "Текст."), ensure_ascii=False),
        encoding="utf-8",
    )
    config_path = tmp_path / "clean.yaml"
    config_path.write_text(
        f"""
input_path: {input_path}
output_run_name: clean_test
continue_on_error: true
log_skipped_articles: false
""",
        encoding="utf-8",
    )
    job = WikipediaCleanJob(
        configuration_service=ConfigurationService(),
        raw_reader=RawArticleJsonlReader(raw_dir),
        cleaning_service=FailingArticleCleaningService(),
        cleaned_writer=CleanedArticleJsonlWriter(processed_dir),
    )

    with caplog.at_level(logging.WARNING, logger="vezilka_text_scraper.jobs.clean"):
        result = job.run(config_path)

    assert result.failed_count == 1
    assert "Failed cleaning raw article 'Географија' (1)" in caplog.text
    assert "forced cleaning failure" in caplog.text
