from pathlib import Path
from typing import Any

import pytest
from sqlalchemy import text
from sqlalchemy.engine import Engine

from vezilka_text_scraper.adapters import database
from vezilka_text_scraper.adapters.database import ArticleDatabaseAdapter
from vezilka_text_scraper.models.article import CleanedArticle, CleanedSection
from vezilka_text_scraper.services.persist_config import DatabaseConfig
from vezilka_text_scraper.shared import env_variables
from vezilka_text_scraper.shared.exceptions import AdapterError


def _article(page_id: int = 1, title: str = "Географија") -> CleanedArticle:
    section = CleanedSection(
        heading=title,
        content=f"{title} е наука.",
        word_count=3,
        char_count=17,
        position=0,
    )
    return CleanedArticle(
        page_id=page_id,
        title=title,
        url=f"https://mk.wikipedia.org/wiki/{title}",
        language="mk",
        categories=["Категорија:Географија", "Категорија:Наука"],
        revision_id=10 + page_id,
        last_modified="2026-01-01T00:00:00Z",
        scraped_at="2026-06-21T00:00:00+00:00",
        cleaned_at="2026-06-21T01:00:00+00:00",
        source_categories=["Географија"],
        clean_text=f"{title}\n\n{title} е наука.",
        word_count=4,
        char_count=30,
        section_count=1,
        sections=[section],
    )


def _database_config(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> DatabaseConfig:
    monkeypatch.setattr(env_variables, "SQLITE_DATABASE_PATH", tmp_path / "corpus.db")
    return DatabaseConfig(type="sqlite")


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
        connection.execute(
            text(
                """
                CREATE TABLE wiki_categories (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    name TEXT NOT NULL UNIQUE
                )
                """
            )
        )
        connection.execute(
            text(
                """
                CREATE TABLE article_wiki_categories (
                    article_id INTEGER NOT NULL,
                    category_id INTEGER NOT NULL
                )
                """
            )
        )
        connection.execute(
            text(
                """
                CREATE TABLE source_categories (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    name TEXT NOT NULL UNIQUE
                )
                """
            )
        )
        connection.execute(
            text(
                """
                CREATE TABLE article_source_categories (
                    article_id INTEGER NOT NULL,
                    category_id INTEGER NOT NULL
                )
                """
            )
        )


def test_sqlite_validation_succeeds_when_schema_exists(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    adapter = ArticleDatabaseAdapter(_database_config(tmp_path, monkeypatch))
    _create_required_schema(adapter.engine)

    adapter.validate_ready()


def test_initialize_schema_creates_missing_sqlite_tables(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    adapter = ArticleDatabaseAdapter(_database_config(tmp_path, monkeypatch))

    result = adapter.initialize_schema()

    assert result.created_schema is False
    assert result.existing_table_count == 0
    assert result.created_table_count == 6
    adapter.validate_ready()


def test_initialize_schema_skips_existing_sqlite_tables(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    adapter = ArticleDatabaseAdapter(_database_config(tmp_path, monkeypatch))
    adapter.initialize_schema()

    result = adapter.initialize_schema()

    assert result.created_schema is False
    assert result.existing_table_count == 6
    assert result.created_table_count == 0


def test_sqlite_validation_fails_when_required_table_is_missing(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    adapter = ArticleDatabaseAdapter(_database_config(tmp_path, monkeypatch))

    with pytest.raises(AdapterError, match="missing required tables"):
        adapter.validate_ready()


def test_sqlite_validation_fails_when_required_column_is_missing(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    adapter = ArticleDatabaseAdapter(_database_config(tmp_path, monkeypatch))
    with adapter.engine.begin() as connection:
        connection.execute(text("CREATE TABLE articles (id INTEGER PRIMARY KEY)"))
        for table_name in [
            "sections",
            "wiki_categories",
            "article_wiki_categories",
            "source_categories",
            "article_source_categories",
        ]:
            connection.execute(text(f"CREATE TABLE {table_name} (id INTEGER PRIMARY KEY)"))

    with pytest.raises(AdapterError, match="missing required columns"):
        adapter.validate_ready()


def test_persist_articles_inserts_article_sections_and_categories(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    adapter = ArticleDatabaseAdapter(_database_config(tmp_path, monkeypatch))
    _create_required_schema(adapter.engine)

    result = adapter.persist_articles([_article()])

    assert result.inserted_count == 1
    assert result.updated_count == 0
    assert result.section_count == 1
    assert result.wiki_category_link_count == 2
    assert result.source_category_link_count == 1
    with adapter.engine.connect() as connection:
        assert connection.execute(text("SELECT count(*) FROM articles")).scalar_one() == 1
        assert connection.execute(text("SELECT count(*) FROM sections")).scalar_one() == 1
        assert connection.execute(text("SELECT count(*) FROM wiki_categories")).scalar_one() == 2
        assert (
            connection.execute(text("SELECT count(*) FROM article_wiki_categories")).scalar_one()
            == 2
        )
        assert connection.execute(text("SELECT count(*) FROM source_categories")).scalar_one() == 1
        assert (
            connection.execute(text("SELECT count(*) FROM article_source_categories")).scalar_one()
            == 1
        )


def test_read_articles_reconstructs_cleaned_articles_from_database(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    adapter = ArticleDatabaseAdapter(_database_config(tmp_path, monkeypatch))
    adapter.initialize_schema()
    adapter.persist_articles(
        [_article(page_id=1, title="Прва"), _article(page_id=2, title="Втора")]
    )

    articles = adapter.read_articles(article_limit=1)

    assert len(articles) == 1
    assert articles[0].title == "Прва"
    assert articles[0].sections[0].heading == "Прва"
    assert articles[0].categories == ["Категорија:Географија", "Категорија:Наука"]
    assert articles[0].source_categories == ["Географија"]


def test_read_articles_allows_unlimited_limit(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    adapter = ArticleDatabaseAdapter(_database_config(tmp_path, monkeypatch))
    adapter.initialize_schema()
    adapter.persist_articles(
        [_article(page_id=1, title="Прва"), _article(page_id=2, title="Втора")]
    )

    articles = adapter.read_articles(article_limit=None)

    assert [article.title for article in articles] == ["Прва", "Втора"]


def test_persist_articles_upserts_and_replaces_sections(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    adapter = ArticleDatabaseAdapter(_database_config(tmp_path, monkeypatch))
    _create_required_schema(adapter.engine)
    adapter.persist_articles([_article(page_id=1, title="Старо")])
    updated_article = _article(page_id=1, title="Ново")
    updated_article = updated_article.model_copy(
        update={
            "sections": [
                CleanedSection(
                    heading="Ново",
                    content="Прва нова секција.",
                    word_count=3,
                    char_count=18,
                    position=0,
                ),
                CleanedSection(
                    heading="Историја",
                    content="Втора нова секција.",
                    word_count=3,
                    char_count=19,
                    position=1,
                ),
            ],
            "section_count": 2,
            "categories": ["Категорија:Историја"],
            "source_categories": ["Историја"],
        }
    )

    result = adapter.persist_articles([updated_article])

    assert result.inserted_count == 0
    assert result.updated_count == 1
    assert result.section_count == 2
    with adapter.engine.connect() as connection:
        assert connection.execute(text("SELECT title FROM articles")).scalar_one() == "Ново"
        assert connection.execute(text("SELECT count(*) FROM sections")).scalar_one() == 2
        assert (
            connection.execute(text("SELECT count(*) FROM article_wiki_categories")).scalar_one()
            == 1
        )
        assert (
            connection.execute(text("SELECT count(*) FROM article_source_categories")).scalar_one()
            == 1
        )


def test_persist_articles_rolls_back_on_write_error(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    adapter = ArticleDatabaseAdapter(_database_config(tmp_path, monkeypatch))
    with adapter.engine.begin() as connection:
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
                    position INTEGER NOT NULL,
                    UNIQUE(article_id, position)
                )
                """
            )
        )
        connection.execute(
            text("CREATE TABLE wiki_categories (id INTEGER PRIMARY KEY, name TEXT UNIQUE)")
        )
        connection.execute(
            text("CREATE TABLE article_wiki_categories (article_id INTEGER, category_id INTEGER)")
        )
        connection.execute(
            text("CREATE TABLE source_categories (id INTEGER PRIMARY KEY, name TEXT UNIQUE)")
        )
        connection.execute(
            text("CREATE TABLE article_source_categories (article_id INTEGER, category_id INTEGER)")
        )
    article = _article().model_copy(
        update={
            "sections": [
                CleanedSection(
                    heading="Прва",
                    content="Прва секција.",
                    word_count=2,
                    char_count=13,
                    position=0,
                ),
                CleanedSection(
                    heading="Втора",
                    content="Втора секција.",
                    word_count=2,
                    char_count=14,
                    position=0,
                ),
            ],
            "section_count": 2,
        }
    )

    with pytest.raises(AdapterError):
        adapter.persist_articles([article])

    with adapter.engine.connect() as connection:
        assert connection.execute(text("SELECT count(*) FROM articles")).scalar_one() == 0


class FakeConnection:
    def __enter__(self) -> "FakeConnection":
        return self

    def __exit__(self, *args: object) -> None:
        return None

    def execute(self, *_args: object, **_kwargs: object) -> object:
        return object()


class FakeUrl:
    def render_as_string(self, hide_password: bool) -> str:
        return "postgresql+psycopg://user:***@localhost/db"


class FakeEngine:
    url = FakeUrl()

    def connect(self) -> FakeConnection:
        return FakeConnection()


class FakeInspector:
    def __init__(self, schemas: set[str]) -> None:
        self._schemas = schemas

    def get_schema_names(self) -> list[str]:
        return sorted(self._schemas)

    def get_table_names(self, schema: str | None = None) -> list[str]:
        return sorted(database.REQUIRED_TABLE_COLUMNS)

    def get_columns(self, table_name: str, schema: str | None = None) -> list[dict[str, Any]]:
        return [{"name": column} for column in database.REQUIRED_TABLE_COLUMNS[table_name]]


def test_postgresql_validation_uses_configured_schema(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(database, "create_engine", lambda *_args, **_kwargs: FakeEngine())
    monkeypatch.setattr(database, "inspect", lambda _engine: FakeInspector({"corpus"}))
    monkeypatch.setattr(env_variables, "POSTGRES_SCHEMA", "corpus")
    adapter = ArticleDatabaseAdapter(DatabaseConfig(type="postgresql"))

    adapter.validate_ready()


def test_postgresql_validation_fails_when_schema_is_missing(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(database, "create_engine", lambda *_args, **_kwargs: FakeEngine())
    monkeypatch.setattr(database, "inspect", lambda _engine: FakeInspector({"public"}))
    monkeypatch.setattr(env_variables, "POSTGRES_SCHEMA", "corpus")
    adapter = ArticleDatabaseAdapter(DatabaseConfig(type="postgresql"))

    with pytest.raises(AdapterError, match="schema does not exist"):
        adapter.validate_ready()
