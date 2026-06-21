from pathlib import Path


def test_crawl_controls_are_not_env_variables() -> None:
    env_example = Path(".env.example").read_text(encoding="utf-8")
    env_variables_source = Path("src/vezilka_text_scraper/shared/env_variables.py").read_text(
        encoding="utf-8"
    )

    assert "RECURSIVE_CATEGORY_CRAWL" not in env_example
    assert "CATEGORY_MAX_DEPTH" not in env_example
    assert "RECURSIVE_CATEGORY_CRAWL =" not in env_variables_source
    assert "CATEGORY_MAX_DEPTH =" not in env_variables_source


def test_database_connection_details_are_env_variables() -> None:
    env_example = Path(".env.example").read_text(encoding="utf-8")
    env_variables_source = Path("src/vezilka_text_scraper/shared/env_variables.py").read_text(
        encoding="utf-8"
    )

    assert "DATABASE_URL" not in env_example
    assert "DATABASE_URL =" not in env_variables_source
    assert "SQLITE_DATABASE_PATH" in env_example
    assert "POSTGRES_HOST" in env_example
    assert "POSTGRES_PORT" in env_example
    assert "POSTGRES_USER" in env_example
    assert "POSTGRES_PASSWORD" in env_example
    assert "POSTGRES_DATABASE" in env_example
    assert "POSTGRES_SCHEMA" in env_example
