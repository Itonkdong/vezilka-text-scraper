import json
import logging
from pathlib import Path
from typing import cast

import pytest

from vezilka_text_scraper.adapters.mediawiki import CategoryMember, MediaWikiAdapter, RawArticle
from vezilka_text_scraper.adapters.raw_storage import RawArticleJsonlStorageAdapter
from vezilka_text_scraper.jobs.scrape import WikipediaScrapeJob
from vezilka_text_scraper.services.article_discovery import ArticleDiscoveryService
from vezilka_text_scraper.services.configuration import ConfigurationService


class FakeMediaWikiAdapter:
    def __init__(self) -> None:
        self.fetched_page_ids: list[int] = []

    def list_category_members(self, category: str, namespace: int) -> list[CategoryMember]:
        return [
            CategoryMember(page_id=1, title="Прва", namespace=0),
            CategoryMember(page_id=2, title="Втора", namespace=0),
            CategoryMember(page_id=3, title="Трета", namespace=0),
        ]

    def fetch_raw_article(
        self,
        page_id: int,
        language: str,
        source_categories: list[str],
        scraped_at: str,
        include_redirects: bool,
    ) -> RawArticle | None:
        self.fetched_page_ids.append(page_id)
        return RawArticle(
            page_id=page_id,
            title=f"Статија {page_id}",
            url=f"https://mk.wikipedia.org/wiki/{page_id}",
            language=language,
            categories=[],
            revision_id=page_id,
            last_modified="2026-01-01T00:00:00Z",
            scraped_at=scraped_at,
            source_categories=source_categories,
            raw_wikitext=f"Текст {page_id}",
        )


def test_scrape_job_writes_raw_articles_in_batches(
    tmp_path: Path,
    caplog: pytest.LogCaptureFixture,
) -> None:
    raw_dir = tmp_path / "raw"
    config_path = tmp_path / "scrape.yaml"
    config_path.write_text(
        """
categories:
  - Географија
recursive: false
request_delay_seconds: 0
batch_size: 2
output_run_name: scrape_test
""",
        encoding="utf-8",
    )
    fake_mediawiki = FakeMediaWikiAdapter()
    mediawiki_adapter = cast(MediaWikiAdapter, fake_mediawiki)
    job = WikipediaScrapeJob(
        configuration_service=ConfigurationService(),
        discovery_service=ArticleDiscoveryService(mediawiki_adapter),
        mediawiki_adapter=mediawiki_adapter,
        storage_adapter=RawArticleJsonlStorageAdapter(raw_dir),
    )

    with caplog.at_level(logging.INFO, logger="vezilka_text_scraper.jobs.scrape"):
        result = job.run(config_path)

    records = [
        json.loads(line)
        for line in result.output_path.read_text(encoding="utf-8").splitlines()
    ]
    assert result.discovered_count == 3
    assert result.saved_count == 3
    assert result.batch_size == 2
    assert result.batch_count == 2
    assert [record["page_id"] for record in records] == [1, 2, 3]
    assert "Discovering unique Wikipedia articles from configured categories" in caplog.text
    assert "Starting raw article fetch from MediaWiki" in caplog.text
