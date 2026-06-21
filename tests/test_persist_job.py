import json
from pathlib import Path

import pytest
from sqlalchemy import create_engine, text
from sqlalchemy.engine import Engine

from vezilka_text_scraper.adapters.article_jsonl import CleanedArticleJsonlReader
from vezilka_text_scraper.jobs.persist import WikipediaPersistJob
from vezilka_text_scraper.services.configuration import ConfigurationService
from vezilka_text_scraper.shared import env_variables
from vezilka_text_scraper.shared.exceptions import AdapterError


def _processed_record(page_id: int, title: str) -> dict[str, object]:
    return {
        "page_id": page_id,
        "title": title,
        "url": f"https://mk.wikipedia.org/wiki/{title}",
        "language": "mk",
        "categories": ["Категорија:Географија"],
        "revision_id": 10 + page_id,
        "last_modified": "2026-01-01T00:00:00Z",
        "scraped_at": "2026-06-21T00:00:00+00:00",
        "cleaned_at": "2026-06-21T01:00:00+00:00",
        "source_categories": ["Географија"],
        "clean_text": f"{title}\n\n{title} е наука.",
        "word_count": 4,
        "char_count": 30,
        "section_count": 1,
        "sections": [
            {
                "heading": title,
                "content": f"{title} е наука.",
                "word_count": 3,
                "char_count": 17,
                "position": 0,
            }
        ],
    }


def _create_required_schema(engine: Engine) -> None:
    with engine.begin() as connection:
        connection.execute(
            text(
                """
                CREATE TABLE articles (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    page_id INTEGER NOT NULL UNIQUE,
                    title TEXT NOT NULL,
                    url TEXT NOT NULL,
                    language TEXT NOT NULL,
                    revision_id INTEGER NOT NULL,
                    last_modified TEXT NOT NULL,
                    scraped_at TEXT NOT NULL,
                    cleaned_at TEXT NOT NULL,
                    clean_text TEXT NOT NULL,
                    word_count INTEGER NOT NULL,
                    char_count INTEGER NOT NULL,
                    section_count INTEGER NOT NULL,
                    sensitivity_status TEXT NOT NULL,
                    sensitivity_keywords TEXT NOT NULL,
                    created_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL
                )
                """
            )
        )
        connection.execute(
            text(
                """
                CREATE TABLE sections (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    article_id INTEGER NOT NULL,
                    heading TEXT NOT NULL,
                    content TEXT NOT NULL,
                    word_count INTEGER NOT NULL,
                    char_count INTEGER NOT NULL,
                    position INTEGER NOT NULL
                )
                """
            )
        )
        connection.execute(text("CREATE TABLE wiki_categories (id INTEGER PRIMARY KEY, name TEXT)"))
        connection.execute(
            text("CREATE TABLE article_wiki_categories (article_id INTEGER, category_id INTEGER)")
        )
        connection.execute(
            text("CREATE TABLE source_categories (id INTEGER PRIMARY KEY, name TEXT)")
        )
        connection.execute(
            text("CREATE TABLE article_source_categories (article_id INTEGER, category_id INTEGER)")
        )


def test_persist_job_reads_newest_processed_file_and_persists_counts(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    processed_dir = tmp_path / "processed"
    processed_dir.mkdir()
    older_path = processed_dir / "older.jsonl"
    newer_path = processed_dir / "newer.jsonl"
    older_path.write_text(
        json.dumps(_processed_record(1, "Старо"), ensure_ascii=False),
        encoding="utf-8",
    )
    newer_path.write_text(
        "\n".join(
            [
                json.dumps(_processed_record(2, "Прво"), ensure_ascii=False),
                json.dumps(_processed_record(3, "Второ"), ensure_ascii=False),
            ]
        ),
        encoding="utf-8",
    )
    database_path = tmp_path / "corpus.db"
    monkeypatch.setattr(env_variables, "SQLITE_DATABASE_PATH", database_path)
    engine = create_engine(f"sqlite:///{database_path}", future=True)
    _create_required_schema(engine)
    config_path = tmp_path / "persist.yaml"
    config_path.write_text(
        """
article_limit: 1
batch_size: 1
database:
  type: sqlite
""",
        encoding="utf-8",
    )
    job = WikipediaPersistJob(
        configuration_service=ConfigurationService(),
        reader=CleanedArticleJsonlReader(processed_dir),
    )

    result = job.run(config_path)

    assert result.input_path == newer_path
    assert result.read_count == 1
    assert result.inserted_count == 1
    assert result.updated_count == 0
    assert result.section_count == 1
    assert result.wiki_category_link_count == 1
    assert result.source_category_link_count == 1
    assert result.batch_size == 1
    assert result.batch_count == 1
    with engine.connect() as connection:
        assert connection.execute(text("SELECT title FROM articles")).scalar_one() == "Прво"


def test_persist_job_fails_when_schema_is_missing(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    processed_dir = tmp_path / "processed"
    processed_dir.mkdir()
    input_path = processed_dir / "processed.jsonl"
    input_path.write_text(
        json.dumps(_processed_record(1, "Географија"), ensure_ascii=False),
        encoding="utf-8",
    )
    database_path = tmp_path / "missing_schema.db"
    monkeypatch.setattr(env_variables, "SQLITE_DATABASE_PATH", database_path)
    config_path = tmp_path / "persist.yaml"
    config_path.write_text(
        f"""
input_path: {input_path}
database:
  type: sqlite
""",
        encoding="utf-8",
    )
    job = WikipediaPersistJob(
        configuration_service=ConfigurationService(),
        reader=CleanedArticleJsonlReader(processed_dir),
    )

    with pytest.raises(AdapterError, match="missing required tables"):
        job.run(config_path)


def test_persist_job_with_init_creates_schema_before_persisting(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    processed_dir = tmp_path / "processed"
    processed_dir.mkdir()
    input_path = processed_dir / "processed.jsonl"
    input_path.write_text(
        json.dumps(_processed_record(1, "Географија"), ensure_ascii=False),
        encoding="utf-8",
    )
    database_path = tmp_path / "fresh.db"
    monkeypatch.setattr(env_variables, "SQLITE_DATABASE_PATH", database_path)
    config_path = tmp_path / "persist.yaml"
    config_path.write_text(
        f"""
input_path: {input_path}
database:
  type: sqlite
""",
        encoding="utf-8",
    )
    job = WikipediaPersistJob(
        configuration_service=ConfigurationService(),
        reader=CleanedArticleJsonlReader(processed_dir),
    )

    result = job.run(config_path=config_path, with_init=True)

    assert result.initialized_database is True
    assert result.inserted_count == 1
    with create_engine(f"sqlite:///{database_path}", future=True).connect() as connection:
        assert connection.execute(text("SELECT title FROM articles")).scalar_one() == "Географија"
