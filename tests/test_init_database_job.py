from pathlib import Path

import pytest
from sqlalchemy import create_engine, inspect

from vezilka_text_scraper.jobs.init_database import InitDatabaseJob
from vezilka_text_scraper.services.configuration import ConfigurationService
from vezilka_text_scraper.shared import env_variables


def test_init_database_job_creates_schema_and_skips_on_rerun(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    database_path = tmp_path / "corpus.db"
    monkeypatch.setattr(env_variables, "SQLITE_DATABASE_PATH", database_path)
    config_path = tmp_path / "init_database.yaml"
    config_path.write_text(
        """
database:
  type: sqlite
""",
        encoding="utf-8",
    )
    job = InitDatabaseJob(configuration_service=ConfigurationService())

    first_result = job.run(config_path)
    second_result = job.run(config_path)

    assert first_result.created_table_count == 6
    assert first_result.existing_table_count == 0
    assert second_result.created_table_count == 0
    assert second_result.existing_table_count == 6
    inspector = inspect(create_engine(f"sqlite:///{database_path}", future=True))
    assert set(inspector.get_table_names()) == {
        "articles",
        "sections",
        "wiki_categories",
        "article_wiki_categories",
        "source_categories",
        "article_source_categories",
    }
