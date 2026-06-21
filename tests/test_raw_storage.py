import json
from pathlib import Path

from vezilka_text_scraper.adapters.mediawiki import RawArticle
from vezilka_text_scraper.adapters.raw_storage import RawArticleJsonlStorageAdapter


def test_raw_storage_writes_jsonl_records(tmp_path: Path) -> None:
    output_path = tmp_path / "raw" / "sample.jsonl"
    article = RawArticle(
        page_id=1,
        title="Македонија",
        url="https://mk.wikipedia.org/wiki/Македонија",
        language="mk",
        categories=["Категорија:Географија"],
        revision_id=10,
        last_modified="2024-01-01T00:00:00Z",
        scraped_at="2026-01-01T00:00:00+00:00",
        source_categories=["Географија"],
        raw_wikitext="'''Македонија'''",
    )

    count = RawArticleJsonlStorageAdapter(tmp_path / "raw").write_articles(
        [article],
        output_path,
    )

    records = [json.loads(line) for line in output_path.read_text(encoding="utf-8").splitlines()]
    assert count == 1
    assert records[0]["page_id"] == 1
    assert records[0]["raw_wikitext"] == "'''Македонија'''"


def test_raw_storage_appends_batches(tmp_path: Path) -> None:
    output_path = tmp_path / "raw" / "sample.jsonl"
    articles = [
        RawArticle(
            page_id=page_id,
            title=f"Статија {page_id}",
            url=f"https://mk.wikipedia.org/wiki/{page_id}",
            language="mk",
            categories=[],
            revision_id=page_id,
            last_modified="2024-01-01T00:00:00Z",
            scraped_at="2026-01-01T00:00:00+00:00",
            source_categories=["Географија"],
            raw_wikitext=f"Текст {page_id}",
        )
        for page_id in [1, 2]
    ]
    storage = RawArticleJsonlStorageAdapter(tmp_path / "raw")

    storage.write_article_batch([articles[0]], output_path, append=False)
    storage.write_article_batch([articles[1]], output_path, append=True)

    records = [json.loads(line) for line in output_path.read_text(encoding="utf-8").splitlines()]
    assert [record["page_id"] for record in records] == [1, 2]
