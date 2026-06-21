import json
from pathlib import Path

import pytest

from vezilka_text_scraper.adapters.article_jsonl import (
    CleanedArticleJsonlReader,
    CleanedArticleJsonlWriter,
    RawArticleJsonlReader,
)
from vezilka_text_scraper.models.article import CleanedArticle, CleanedSection
from vezilka_text_scraper.shared.exceptions import AdapterError


def _raw_record(page_id: int = 1) -> dict[str, object]:
    return {
        "page_id": page_id,
        "title": "Географија",
        "url": "https://mk.wikipedia.org/wiki/Географија",
        "language": "mk",
        "categories": ["Категорија:Географија"],
        "revision_id": 10,
        "last_modified": "2026-01-01T00:00:00Z",
        "scraped_at": "2026-06-21T00:00:00+00:00",
        "source_categories": ["Географија"],
        "raw_wikitext": "'''Географија''' е наука.",
    }


def test_raw_reader_resolves_latest_input_path(tmp_path: Path) -> None:
    raw_dir = tmp_path / "raw"
    raw_dir.mkdir()
    older_path = raw_dir / "older.jsonl"
    newer_path = raw_dir / "newer.jsonl"
    older_path.write_text(json.dumps(_raw_record(1), ensure_ascii=False), encoding="utf-8")
    newer_path.write_text(json.dumps(_raw_record(2), ensure_ascii=False), encoding="utf-8")

    assert RawArticleJsonlReader(raw_dir).resolve_input_path(None) == newer_path


def test_raw_reader_reads_valid_jsonl(tmp_path: Path) -> None:
    input_path = tmp_path / "raw.jsonl"
    input_path.write_text(json.dumps(_raw_record(), ensure_ascii=False), encoding="utf-8")

    articles = RawArticleJsonlReader(tmp_path).read_articles(input_path)

    assert len(articles) == 1
    assert articles[0].title == "Географија"


def test_raw_reader_iterates_batches(tmp_path: Path) -> None:
    input_path = tmp_path / "raw.jsonl"
    input_path.write_text(
        "\n".join(json.dumps(_raw_record(page_id), ensure_ascii=False) for page_id in [1, 2, 3]),
        encoding="utf-8",
    )

    batches = list(RawArticleJsonlReader(tmp_path).iter_article_batches(input_path, 2))

    assert [[article.page_id for article in batch] for batch in batches] == [[1, 2], [3]]


def test_raw_reader_rejects_invalid_records(tmp_path: Path) -> None:
    input_path = tmp_path / "raw.jsonl"
    input_path.write_text('{"page_id": 1}\n', encoding="utf-8")

    with pytest.raises(AdapterError):
        RawArticleJsonlReader(tmp_path).read_articles(input_path)


def test_cleaned_writer_writes_jsonl(tmp_path: Path) -> None:
    output_path = tmp_path / "processed" / "clean.jsonl"
    section = CleanedSection(
        heading="Географија",
        content="Географија е наука.",
        word_count=3,
        char_count=17,
        position=0,
    )
    article = CleanedArticle(
        page_id=1,
        title="Географија",
        url="https://mk.wikipedia.org/wiki/Географија",
        language="mk",
        categories=["Категорија:Географија"],
        revision_id=10,
        last_modified="2026-01-01T00:00:00Z",
        scraped_at="2026-06-21T00:00:00+00:00",
        cleaned_at="2026-06-21T01:00:00+00:00",
        source_categories=["Географија"],
        clean_text="Географија\n\nГеографија е наука.",
        word_count=4,
        char_count=30,
        section_count=1,
        sections=[section],
    )

    count = CleanedArticleJsonlWriter(tmp_path / "processed").write_articles(
        [article],
        output_path,
    )

    records = [json.loads(line) for line in output_path.read_text(encoding="utf-8").splitlines()]
    assert count == 1
    assert records[0]["title"] == "Географија"
    assert records[0]["sections"][0]["heading"] == "Географија"


def test_cleaned_writer_appends_batches(tmp_path: Path) -> None:
    output_path = tmp_path / "processed" / "clean.jsonl"
    section = CleanedSection(
        heading="Географија",
        content="Географија е наука.",
        word_count=3,
        char_count=17,
        position=0,
    )
    articles = [
        CleanedArticle(
            page_id=page_id,
            title=f"Статија {page_id}",
            url=f"https://mk.wikipedia.org/wiki/{page_id}",
            language="mk",
            categories=[],
            revision_id=page_id,
            last_modified="2026-01-01T00:00:00Z",
            scraped_at="2026-06-21T00:00:00+00:00",
            cleaned_at="2026-06-21T01:00:00+00:00",
            source_categories=["Географија"],
            clean_text="Географија\n\nГеографија е наука.",
            word_count=4,
            char_count=30,
            section_count=1,
            sections=[section],
        )
        for page_id in [1, 2]
    ]
    writer = CleanedArticleJsonlWriter(tmp_path / "processed")

    writer.write_article_batch([articles[0]], output_path, append=False)
    writer.write_article_batch([articles[1]], output_path, append=True)

    records = [json.loads(line) for line in output_path.read_text(encoding="utf-8").splitlines()]
    assert [record["page_id"] for record in records] == [1, 2]


def test_cleaned_reader_allows_unlimited_article_limit(tmp_path: Path) -> None:
    input_path = tmp_path / "processed.jsonl"
    section = {
        "heading": "Географија",
        "content": "Географија е наука.",
        "word_count": 3,
        "char_count": 17,
        "position": 0,
    }
    base_record = {
        "url": "https://mk.wikipedia.org/wiki/Географија",
        "language": "mk",
        "categories": ["Категорија:Географија"],
        "revision_id": 10,
        "last_modified": "2026-01-01T00:00:00Z",
        "scraped_at": "2026-06-21T00:00:00+00:00",
        "cleaned_at": "2026-06-21T01:00:00+00:00",
        "source_categories": ["Географија"],
        "clean_text": "Географија\n\nГеографија е наука.",
        "word_count": 4,
        "char_count": 30,
        "section_count": 1,
        "sections": [section],
    }
    records = [
        {"page_id": 1, "title": "Прва", **base_record},
        {"page_id": 2, "title": "Втора", **base_record},
    ]
    input_path.write_text(
        "\n".join(json.dumps(record, ensure_ascii=False) for record in records),
        encoding="utf-8",
    )

    articles = CleanedArticleJsonlReader(tmp_path).read_articles(input_path, None)

    assert [article.title for article in articles] == ["Прва", "Втора"]


def test_cleaned_reader_iterates_batches_with_article_limit(tmp_path: Path) -> None:
    input_path = tmp_path / "processed.jsonl"
    section = {
        "heading": "Географија",
        "content": "Географија е наука.",
        "word_count": 3,
        "char_count": 17,
        "position": 0,
    }
    base_record = {
        "url": "https://mk.wikipedia.org/wiki/Географија",
        "language": "mk",
        "categories": ["Категорија:Географија"],
        "revision_id": 10,
        "last_modified": "2026-01-01T00:00:00Z",
        "scraped_at": "2026-06-21T00:00:00+00:00",
        "cleaned_at": "2026-06-21T01:00:00+00:00",
        "source_categories": ["Географија"],
        "clean_text": "Географија\n\nГеографија е наука.",
        "word_count": 4,
        "char_count": 30,
        "section_count": 1,
        "sections": [section],
    }
    records = [
        {"page_id": 1, "title": "Прва", **base_record},
        {"page_id": 2, "title": "Втора", **base_record},
        {"page_id": 3, "title": "Трета", **base_record},
    ]
    input_path.write_text(
        "\n".join(json.dumps(record, ensure_ascii=False) for record in records),
        encoding="utf-8",
    )

    batches = list(CleanedArticleJsonlReader(tmp_path).iter_article_batches(input_path, 2, 2))

    assert [[article.page_id for article in batch] for batch in batches] == [[1, 2]]
