"""SQLAlchemy database adapter for persisted corpus records."""

from __future__ import annotations

from datetime import UTC, datetime
from pathlib import Path
from typing import SupportsInt

from pydantic import BaseModel, ConfigDict, Field
from sqlalchemy import (
    Column,
    Engine,
    ForeignKey,
    Integer,
    MetaData,
    Table,
    Text,
    UniqueConstraint,
    create_engine,
    inspect,
    text,
)
from sqlalchemy.engine import Connection
from sqlalchemy.exc import SQLAlchemyError

from vezilka_text_scraper.models.article import CleanedArticle, CleanedSection
from vezilka_text_scraper.services.persist_config import DatabaseConfig
from vezilka_text_scraper.shared.exceptions import AdapterError

REQUIRED_TABLE_COLUMNS = {
    "articles": {
        "id",
        "page_id",
        "title",
        "url",
        "language",
        "revision_id",
        "last_modified",
        "scraped_at",
        "cleaned_at",
        "clean_text",
        "word_count",
        "char_count",
        "section_count",
        "created_at",
        "updated_at",
    },
    "sections": {
        "id",
        "article_id",
        "heading",
        "content",
        "word_count",
        "char_count",
        "position",
    },
    "wiki_categories": {"id", "name"},
    "article_wiki_categories": {"article_id", "category_id"},
    "source_categories": {"id", "name"},
    "article_source_categories": {"article_id", "category_id"},
}


class DatabasePersistResult(BaseModel):
    """Database persistence counts."""

    model_config = ConfigDict(frozen=True)

    inserted_count: int = Field(ge=0)
    updated_count: int = Field(ge=0)
    section_count: int = Field(ge=0)
    wiki_category_link_count: int = Field(ge=0)
    source_category_link_count: int = Field(ge=0)


class DatabaseInitResult(BaseModel):
    """Database initialization counts."""

    model_config = ConfigDict(frozen=True)

    created_schema: bool = False
    existing_table_count: int = Field(ge=0)
    created_table_count: int = Field(ge=0)


class ArticleDatabaseAdapter:
    """Persist cleaned articles into a SQL database."""

    def __init__(self, database_config: DatabaseConfig) -> None:
        self._database_config = database_config
        self._engine = create_engine(database_config.url, future=True)

    @property
    def engine(self) -> Engine:
        """Return the SQLAlchemy engine."""
        return self._engine

    def validate_ready(self) -> None:
        """Validate connection, schema, tables, and required columns.

        Raises:
            AdapterError: If the target database is not ready for persistence.
        """
        try:
            with self._engine.connect() as connection:
                connection.execute(text("SELECT 1"))

            inspector = inspect(self._engine)
            schema = self._effective_schema()
            if self._database_config.type == "postgresql":
                available_schemas = set(inspector.get_schema_names())
                if schema not in available_schemas:
                    raise AdapterError(f"Database schema does not exist: {schema}")

            existing_tables = set(inspector.get_table_names(schema=schema))
            missing_tables = sorted(set(REQUIRED_TABLE_COLUMNS) - existing_tables)
            if missing_tables:
                raise AdapterError(
                    "Database is missing required tables: " + ", ".join(missing_tables)
                )

            for table_name, required_columns in REQUIRED_TABLE_COLUMNS.items():
                existing_columns = {
                    column["name"]
                    for column in inspector.get_columns(table_name, schema=schema)
                }
                missing_columns = sorted(required_columns - existing_columns)
                if missing_columns:
                    raise AdapterError(
                        f"Database table '{table_name}' is missing required columns: "
                        + ", ".join(missing_columns)
                    )
        except AdapterError:
            raise
        except SQLAlchemyError as error:
            raise AdapterError("Could not validate database connection or schema") from error

    def initialize_schema(self) -> DatabaseInitResult:
        """Create missing schema objects and validate the database is ready."""
        try:
            self._ensure_sqlite_parent_directory()
            created_schema = self._ensure_database_schema()
            inspector = inspect(self._engine)
            schema = self._effective_schema()
            existing_tables = set(inspector.get_table_names(schema=schema))
            missing_tables = set(REQUIRED_TABLE_COLUMNS) - existing_tables

            metadata = self._build_metadata()
            metadata.create_all(self._engine)
            self.validate_ready()
        except AdapterError:
            raise
        except SQLAlchemyError as error:
            raise AdapterError("Could not initialize database schema") from error

        return DatabaseInitResult(
            created_schema=created_schema,
            existing_table_count=len(existing_tables & set(REQUIRED_TABLE_COLUMNS)),
            created_table_count=len(missing_tables),
        )

    def persist_articles(self, articles: list[CleanedArticle]) -> DatabasePersistResult:
        """Persist cleaned article records in a single transaction."""
        inserted_count = 0
        updated_count = 0
        section_count = 0
        wiki_category_link_count = 0
        source_category_link_count = 0

        try:
            self.validate_ready()
            with self._engine.begin() as connection:
                for article in articles:
                    article_id = self._get_article_id(connection, article.page_id)
                    if article_id is None:
                        article_id = self._insert_article(connection, article)
                        inserted_count += 1
                    else:
                        self._update_article(connection, article_id, article)
                        updated_count += 1

                    self._replace_sections(connection, article_id, article)
                    section_count += len(article.sections)

                    wiki_category_link_count += self._replace_category_links(
                        connection=connection,
                        article_id=article_id,
                        category_names=article.categories,
                        category_table="wiki_categories",
                        relationship_table="article_wiki_categories",
                    )
                    source_category_link_count += self._replace_category_links(
                        connection=connection,
                        article_id=article_id,
                        category_names=article.source_categories,
                        category_table="source_categories",
                        relationship_table="article_source_categories",
                    )
        except AdapterError:
            raise
        except SQLAlchemyError as error:
            raise AdapterError("Could not persist cleaned articles") from error

        return DatabasePersistResult(
            inserted_count=inserted_count,
            updated_count=updated_count,
            section_count=section_count,
            wiki_category_link_count=wiki_category_link_count,
            source_category_link_count=source_category_link_count,
        )

    def read_articles(self, article_limit: int | None) -> list[CleanedArticle]:
        """Read cleaned article records from the persisted database tables."""
        try:
            self.validate_ready()
            limit_clause = "" if article_limit is None else "LIMIT :article_limit"
            params = {} if article_limit is None else {"article_limit": article_limit}
            with self._engine.connect() as connection:
                article_rows = connection.execute(
                    text(
                        f"""
                        SELECT id, page_id, title, url, language, revision_id,
                               last_modified, scraped_at, cleaned_at, clean_text,
                               word_count, char_count, section_count
                        FROM {self._table('articles')}
                        ORDER BY id
                        {limit_clause}
                        """
                    ),
                    params,
                ).mappings()
                return [
                    self._build_cleaned_article_from_row(connection, dict(article_row))
                    for article_row in article_rows
                ]
        except AdapterError:
            raise
        except SQLAlchemyError as error:
            raise AdapterError("Could not read cleaned articles from database") from error

    def read_articles_by_page_ids(
        self,
        page_ids: list[int],
        article_limit: int,
    ) -> list[CleanedArticle]:
        """Read persisted articles for the given page ids, preserving page id order."""
        limited_page_ids = page_ids[:article_limit]
        if not limited_page_ids:
            return []

        try:
            self.validate_ready()
            with self._engine.connect() as connection:
                articles_by_page_id: dict[int, CleanedArticle] = {}
                for page_id in limited_page_ids:
                    article_row = connection.execute(
                        text(
                            f"""
                            SELECT id, page_id, title, url, language, revision_id,
                                   last_modified, scraped_at, cleaned_at, clean_text,
                                   word_count, char_count, section_count
                            FROM {self._table('articles')}
                            WHERE page_id = :page_id
                            """
                        ),
                        {"page_id": page_id},
                    ).mappings().one_or_none()
                    if article_row is not None:
                        articles_by_page_id[page_id] = self._build_cleaned_article_from_row(
                            connection,
                            dict(article_row),
                        )
                return [
                    articles_by_page_id[page_id]
                    for page_id in limited_page_ids
                    if page_id in articles_by_page_id
                ]
        except AdapterError:
            raise
        except SQLAlchemyError as error:
            raise AdapterError("Could not read cleaned articles from database") from error

    def mask_database_url(self) -> str:
        """Return the database URL with any password hidden."""
        return self._engine.url.render_as_string(hide_password=True)

    def _effective_schema(self) -> str | None:
        if self._database_config.type == "postgresql":
            return self._database_config.schema_name or "public"
        return None

    def _ensure_sqlite_parent_directory(self) -> None:
        if self._database_config.type != "sqlite":
            return
        database_path = self._engine.url.database
        if database_path is None or database_path in {"", ":memory:"}:
            return
        Path(database_path).parent.mkdir(parents=True, exist_ok=True)

    def _ensure_database_schema(self) -> bool:
        schema = self._effective_schema()
        if self._database_config.type != "postgresql" or schema is None:
            return False

        inspector = inspect(self._engine)
        if schema in set(inspector.get_schema_names()):
            return False

        with self._engine.begin() as connection:
            connection.execute(text(f'CREATE SCHEMA IF NOT EXISTS "{schema}"'))
        return True

    def _build_metadata(self) -> MetaData:
        schema = self._effective_schema()
        metadata = MetaData(schema=schema)
        articles = Table(
            "articles",
            metadata,
            Column("id", Integer, primary_key=True),
            Column("page_id", Integer, nullable=False, unique=True),
            Column("title", Text, nullable=False),
            Column("url", Text, nullable=False),
            Column("language", Text, nullable=False),
            Column("revision_id", Integer, nullable=False),
            Column("last_modified", Text, nullable=False),
            Column("scraped_at", Text, nullable=False),
            Column("cleaned_at", Text, nullable=False),
            Column("clean_text", Text, nullable=False),
            Column("word_count", Integer, nullable=False),
            Column("char_count", Integer, nullable=False),
            Column("section_count", Integer, nullable=False),
            Column("created_at", Text, nullable=False),
            Column("updated_at", Text, nullable=False),
        )
        Table(
            "sections",
            metadata,
            Column("id", Integer, primary_key=True),
            Column("article_id", Integer, ForeignKey(articles.c.id), nullable=False),
            Column("heading", Text, nullable=False),
            Column("content", Text, nullable=False),
            Column("word_count", Integer, nullable=False),
            Column("char_count", Integer, nullable=False),
            Column("position", Integer, nullable=False),
            UniqueConstraint("article_id", "position"),
        )
        wiki_categories = Table(
            "wiki_categories",
            metadata,
            Column("id", Integer, primary_key=True),
            Column("name", Text, nullable=False, unique=True),
        )
        source_categories = Table(
            "source_categories",
            metadata,
            Column("id", Integer, primary_key=True),
            Column("name", Text, nullable=False, unique=True),
        )
        Table(
            "article_wiki_categories",
            metadata,
            Column("article_id", Integer, ForeignKey(articles.c.id), nullable=False),
            Column("category_id", Integer, ForeignKey(wiki_categories.c.id), nullable=False),
            UniqueConstraint("article_id", "category_id"),
        )
        Table(
            "article_source_categories",
            metadata,
            Column("article_id", Integer, ForeignKey(articles.c.id), nullable=False),
            Column("category_id", Integer, ForeignKey(source_categories.c.id), nullable=False),
            UniqueConstraint("article_id", "category_id"),
        )
        return metadata

    def _table(self, table_name: str) -> str:
        schema = self._effective_schema()
        if schema is None:
            return table_name
        return f"{schema}.{table_name}"

    def _get_article_id(self, connection: Connection, page_id: int) -> int | None:
        result = connection.execute(
            text(f"SELECT id FROM {self._table('articles')} WHERE page_id = :page_id"),
            {"page_id": page_id},
        ).scalar_one_or_none()
        return int(result) if result is not None else None

    def _insert_article(self, connection: Connection, article: CleanedArticle) -> int:
        now = self._now()
        connection.execute(
            text(
                f"""
                INSERT INTO {self._table('articles')} (
                    page_id, title, url, language, revision_id, last_modified,
                    scraped_at, cleaned_at, clean_text, word_count, char_count,
                    section_count, created_at, updated_at
                )
                VALUES (
                    :page_id, :title, :url, :language, :revision_id, :last_modified,
                    :scraped_at, :cleaned_at, :clean_text, :word_count, :char_count,
                    :section_count, :created_at, :updated_at
                )
                """
            ),
            {
                **self._article_payload(article),
                "created_at": now,
                "updated_at": now,
            },
        )
        article_id = self._get_article_id(connection, article.page_id)
        if article_id is None:
            raise AdapterError(f"Could not retrieve inserted article id: {article.page_id}")
        return article_id

    def _update_article(
        self,
        connection: Connection,
        article_id: int,
        article: CleanedArticle,
    ) -> None:
        connection.execute(
            text(
                f"""
                UPDATE {self._table('articles')}
                SET title = :title,
                    url = :url,
                    language = :language,
                    revision_id = :revision_id,
                    last_modified = :last_modified,
                    scraped_at = :scraped_at,
                    cleaned_at = :cleaned_at,
                    clean_text = :clean_text,
                    word_count = :word_count,
                    char_count = :char_count,
                    section_count = :section_count,
                    updated_at = :updated_at
                WHERE id = :article_id
                """
            ),
            {
                **self._article_payload(article),
                "updated_at": self._now(),
                "article_id": article_id,
            },
        )

    def _replace_sections(
        self,
        connection: Connection,
        article_id: int,
        article: CleanedArticle,
    ) -> None:
        connection.execute(
            text(f"DELETE FROM {self._table('sections')} WHERE article_id = :article_id"),
            {"article_id": article_id},
        )
        for section in article.sections:
            connection.execute(
                text(
                    f"""
                    INSERT INTO {self._table('sections')} (
                        article_id, heading, content, word_count, char_count, position
                    )
                    VALUES (
                        :article_id, :heading, :content, :word_count, :char_count, :position
                    )
                    """
                ),
                {
                    "article_id": article_id,
                    "heading": section.heading,
                    "content": section.content,
                    "word_count": section.word_count,
                    "char_count": section.char_count,
                    "position": section.position,
                },
            )

    def _replace_category_links(
        self,
        connection: Connection,
        article_id: int,
        category_names: list[str],
        category_table: str,
        relationship_table: str,
    ) -> int:
        connection.execute(
            text(
                f"DELETE FROM {self._table(relationship_table)} "
                "WHERE article_id = :article_id"
            ),
            {"article_id": article_id},
        )
        link_count = 0
        for category_name in dict.fromkeys(category_names):
            category_id = self._get_or_create_category(
                connection,
                category_table,
                category_name,
            )
            connection.execute(
                text(
                    f"""
                    INSERT INTO {self._table(relationship_table)} (article_id, category_id)
                    VALUES (:article_id, :category_id)
                    """
                ),
                {"article_id": article_id, "category_id": category_id},
            )
            link_count += 1
        return link_count

    def _get_or_create_category(
        self,
        connection: Connection,
        table_name: str,
        category_name: str,
    ) -> int:
        existing_id = connection.execute(
            text(f"SELECT id FROM {self._table(table_name)} WHERE name = :name"),
            {"name": category_name},
        ).scalar_one_or_none()
        if existing_id is not None:
            return int(existing_id)

        connection.execute(
            text(f"INSERT INTO {self._table(table_name)} (name) VALUES (:name)"),
            {"name": category_name},
        )
        category_id = connection.execute(
            text(f"SELECT id FROM {self._table(table_name)} WHERE name = :name"),
            {"name": category_name},
        ).scalar_one()
        return int(category_id)

    def _build_cleaned_article_from_row(
        self,
        connection: Connection,
        article_row: dict[str, object],
    ) -> CleanedArticle:
        article_id = self._to_int(article_row["id"])
        sections = [
            CleanedSection(
                heading=str(section_row["heading"]),
                content=str(section_row["content"]),
                word_count=self._to_int(section_row["word_count"]),
                char_count=self._to_int(section_row["char_count"]),
                position=self._to_int(section_row["position"]),
            )
            for section_row in connection.execute(
                text(
                    f"""
                    SELECT heading, content, word_count, char_count, position
                    FROM {self._table('sections')}
                    WHERE article_id = :article_id
                    ORDER BY position
                    """
                ),
                {"article_id": article_id},
            ).mappings()
        ]
        categories = self._read_category_names(
            connection=connection,
            article_id=article_id,
            category_table="wiki_categories",
            relationship_table="article_wiki_categories",
        )
        source_categories = self._read_category_names(
            connection=connection,
            article_id=article_id,
            category_table="source_categories",
            relationship_table="article_source_categories",
        )
        return CleanedArticle(
            page_id=self._to_int(article_row["page_id"]),
            title=str(article_row["title"]),
            url=str(article_row["url"]),
            language=str(article_row["language"]),
            categories=categories,
            revision_id=self._to_int(article_row["revision_id"]),
            last_modified=str(article_row["last_modified"]),
            scraped_at=str(article_row["scraped_at"]),
            cleaned_at=str(article_row["cleaned_at"]),
            source_categories=source_categories,
            clean_text=str(article_row["clean_text"]),
            word_count=self._to_int(article_row["word_count"]),
            char_count=self._to_int(article_row["char_count"]),
            section_count=self._to_int(article_row["section_count"]),
            sections=sections,
        )

    def _to_int(self, value: object) -> int:
        if isinstance(value, int | str | bytes | bytearray):
            return int(value)
        if isinstance(value, SupportsInt):
            return int(value)
        raise AdapterError(f"Expected integer database value, got {type(value).__name__}")

    def _read_category_names(
        self,
        connection: Connection,
        article_id: int,
        category_table: str,
        relationship_table: str,
    ) -> list[str]:
        return [
            str(row["name"])
            for row in connection.execute(
                text(
                    f"""
                    SELECT category.name
                    FROM {self._table(category_table)} AS category
                    JOIN {self._table(relationship_table)} AS relationship
                        ON relationship.category_id = category.id
                    WHERE relationship.article_id = :article_id
                    ORDER BY category.name
                    """
                ),
                {"article_id": article_id},
            ).mappings()
        ]

    def _article_payload(self, article: CleanedArticle) -> dict[str, object]:
        return {
            "page_id": article.page_id,
            "title": article.title,
            "url": article.url,
            "language": article.language,
            "revision_id": article.revision_id,
            "last_modified": article.last_modified,
            "scraped_at": article.scraped_at,
            "cleaned_at": article.cleaned_at,
            "clean_text": article.clean_text,
            "word_count": article.word_count,
            "char_count": article.char_count,
            "section_count": article.section_count,
        }

    def _now(self) -> str:
        return datetime.now(UTC).isoformat()
