from pathlib import Path
from typing import cast

import pytest
from pytest import CaptureFixture
from sqlalchemy import create_engine, text

from vezilka_text_scraper.adapters.article_jsonl import (
    CleanedArticleJsonlWriter,
    RawArticleJsonlReader,
)
from vezilka_text_scraper.adapters.mediawiki import CategoryMember, MediaWikiAdapter, RawArticle
from vezilka_text_scraper.adapters.raw_storage import RawArticleJsonlStorageAdapter
from vezilka_text_scraper.jobs.clean import WikipediaCleanJob
from vezilka_text_scraper.jobs.pipeline import WikipediaPipelineJob
from vezilka_text_scraper.jobs.scrape import WikipediaScrapeJob
from vezilka_text_scraper.services.article_cleaning import ArticleCleaningService
from vezilka_text_scraper.services.article_discovery import ArticleDiscoveryService
from vezilka_text_scraper.services.article_display import ArticleDisplayService
from vezilka_text_scraper.services.configuration import ConfigurationService
from vezilka_text_scraper.shared import env_variables


class FakeMediaWikiAdapter:
    def list_category_members(self, category: str, namespace: int) -> list[CategoryMember]:
        return [
            CategoryMember(page_id=1, title="Прва", namespace=0),
            CategoryMember(page_id=2, title="Втора", namespace=0),
        ]

    def fetch_raw_article(
        self,
        page_id: int,
        language: str,
        source_categories: list[str],
        scraped_at: str,
        include_redirects: bool,
    ) -> RawArticle | None:
        title = "Прва" if page_id == 1 else "Втора"
        return RawArticle(
            page_id=page_id,
            title=title,
            url=f"https://mk.wikipedia.org/wiki/{title}",
            language=language,
            categories=["Категорија:Географија"],
            revision_id=10 + page_id,
            last_modified="2026-01-01T00:00:00Z",
            scraped_at=scraped_at,
            source_categories=source_categories,
            raw_wikitext=f"'''{title}''' е енциклопедиска статија со доволно зборови.",
        )


def _write_step_configs(tmp_path: Path) -> dict[str, Path]:
    scrape_config_path = tmp_path / "scrape.yaml"
    scrape_config_path.write_text(
        """
categories:
  - Географија
recursive: false
request_delay_seconds: 0
output_run_name: raw_pipeline
""",
        encoding="utf-8",
    )
    clean_config_path = tmp_path / "clean.yaml"
    clean_config_path.write_text(
        """
output_run_name: clean_pipeline
min_word_count: 0
min_section_word_count: 0
log_skipped_articles: false
""",
        encoding="utf-8",
    )
    persist_config_path = tmp_path / "persist.yaml"
    persist_config_path.write_text(
        """
database:
  type: sqlite
""",
        encoding="utf-8",
    )
    display_config_path = tmp_path / "display.yaml"
    display_config_path.write_text(
        """
source: file
article_limit: 1
""",
        encoding="utf-8",
    )
    return {
        "scrape": scrape_config_path,
        "clean": clean_config_path,
        "persist": persist_config_path,
        "display": display_config_path,
    }


def _build_pipeline_job(tmp_path: Path) -> WikipediaPipelineJob:
    raw_dir = tmp_path / "raw"
    processed_dir = tmp_path / "processed"
    fake_mediawiki = FakeMediaWikiAdapter()
    mediawiki_adapter = cast(MediaWikiAdapter, fake_mediawiki)
    return WikipediaPipelineJob(
        configuration_service=ConfigurationService(),
        scrape_job=WikipediaScrapeJob(
            configuration_service=ConfigurationService(),
            discovery_service=ArticleDiscoveryService(mediawiki_adapter),
            mediawiki_adapter=mediawiki_adapter,
            storage_adapter=RawArticleJsonlStorageAdapter(raw_dir),
        ),
        clean_job=WikipediaCleanJob(
            configuration_service=ConfigurationService(),
            raw_reader=RawArticleJsonlReader(raw_dir),
            cleaning_service=ArticleCleaningService(),
            cleaned_writer=CleanedArticleJsonlWriter(processed_dir),
        ),
        raw_storage=RawArticleJsonlStorageAdapter(raw_dir),
        cleaned_writer=CleanedArticleJsonlWriter(processed_dir),
        display_service=ArticleDisplayService(),
    )


def _write_pipeline_config(
    tmp_path: Path,
    step_configs: dict[str, Path],
    flags: str,
) -> Path:
    pipeline_config_path = tmp_path / "pipeline.yaml"
    pipeline_config_path.write_text(
        f"""
scrape_config_path: {step_configs["scrape"]}
clean_config_path: {step_configs["clean"]}
persist_config_path: {step_configs["persist"]}
display_config_path: {step_configs["display"]}
{flags}
""",
        encoding="utf-8",
    )
    return pipeline_config_path


def test_pipeline_saves_raw_and_cleaned_files_and_displays_from_file(
    tmp_path: Path,
    capsys: CaptureFixture[str],
) -> None:
    step_configs = _write_step_configs(tmp_path)
    pipeline_config_path = _write_pipeline_config(
        tmp_path,
        step_configs,
        """
save_scraped_articles: true
save_cleaned_articles: true
persist_to_database: false
run_display: true
display_source: file
""",
    )

    result = _build_pipeline_job(tmp_path).run(pipeline_config_path)
    captured = capsys.readouterr()

    assert result.raw_fetched_count == 2
    assert result.raw_saved_count == 2
    assert result.cleaned_count == 2
    assert result.clean_saved_count == 2
    assert result.displayed_count == 1
    assert result.raw_output_path.exists()
    assert result.clean_output_path.exists()
    assert "Прва" in captured.out
    assert "Втора" not in captured.out


def test_pipeline_can_skip_raw_file_output(tmp_path: Path) -> None:
    step_configs = _write_step_configs(tmp_path)
    pipeline_config_path = _write_pipeline_config(
        tmp_path,
        step_configs,
        """
save_scraped_articles: false
save_cleaned_articles: true
persist_to_database: false
run_display: false
display_source: file
""",
    )

    result = _build_pipeline_job(tmp_path).run(pipeline_config_path)

    assert result.raw_saved_count == 0
    assert result.raw_output_path == Path("-")
    assert result.clean_saved_count == 2
    assert result.clean_output_path.exists()


def test_pipeline_persists_to_database_and_displays_from_database(
    tmp_path: Path,
    capsys: CaptureFixture[str],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    database_path = tmp_path / "corpus.db"
    monkeypatch.setattr(env_variables, "SQLITE_DATABASE_PATH", database_path)
    step_configs = _write_step_configs(tmp_path)
    display_config_path = step_configs["display"]
    display_config_path.write_text(
        """
source: database
article_limit: 1
""",
        encoding="utf-8",
    )
    pipeline_config_path = _write_pipeline_config(
        tmp_path,
        step_configs,
        """
save_scraped_articles: false
save_cleaned_articles: false
persist_to_database: true
run_display: true
display_source: database
""",
    )

    result = _build_pipeline_job(tmp_path).run(pipeline_config_path)
    captured = capsys.readouterr()

    assert result.clean_saved_count == 0
    assert result.persist_inserted_count == 2
    assert result.displayed_count == 1
    assert "Прва" in captured.out
    with create_engine(f"sqlite:///{database_path}", future=True).connect() as connection:
        assert connection.execute(text("SELECT count(*) FROM articles")).scalar_one() == 2
