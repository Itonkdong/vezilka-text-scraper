from pathlib import Path

import pytest

from vezilka_text_scraper.services.configuration import ConfigurationService
from vezilka_text_scraper.services.persist_config import PersistConfig
from vezilka_text_scraper.shared import env_variables
from vezilka_text_scraper.shared.constants import (
    DEFAULT_DATABASE_TYPE,
    DEFAULT_PERSIST_ARTICLE_LIMIT,
    DEFAULT_PERSIST_BATCH_SIZE,
)
from vezilka_text_scraper.shared.exceptions import ServiceError


def test_load_full_persist_config(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(env_variables, "POSTGRES_HOST", "localhost")
    monkeypatch.setattr(env_variables, "POSTGRES_PORT", 5432)
    monkeypatch.setattr(env_variables, "POSTGRES_USER", "user")
    monkeypatch.setattr(env_variables, "POSTGRES_PASSWORD", "password")
    monkeypatch.setattr(env_variables, "POSTGRES_DATABASE", "vezilka")
    monkeypatch.setattr(env_variables, "POSTGRES_SCHEMA", "corpus")
    config_path = tmp_path / "persist.yaml"
    config_path.write_text(
        """
input_path: data/processed/sample.jsonl
article_limit: 10
batch_size: 9
database:
  type: postgres
""",
        encoding="utf-8",
    )

    config = ConfigurationService().load(config_path, PersistConfig)

    assert config.input_path == Path("data/processed/sample.jsonl")
    assert config.article_limit == 10
    assert config.batch_size == 9
    assert config.database.type == "postgresql"
    assert config.database.url == "postgresql+psycopg://user:password@localhost:5432/vezilka"
    assert config.database.schema_name == "corpus"


def test_load_partial_persist_config_uses_defaults(tmp_path: Path) -> None:
    config_path = tmp_path / "persist.yaml"
    config_path.write_text("", encoding="utf-8")

    config = ConfigurationService().load(config_path, PersistConfig)

    assert config.input_path is None
    assert config.article_limit == DEFAULT_PERSIST_ARTICLE_LIMIT
    assert config.batch_size == DEFAULT_PERSIST_BATCH_SIZE
    assert config.database.type == DEFAULT_DATABASE_TYPE
    assert config.database.url == "sqlite:///data/vezilka_corpus.db"
    assert config.database.schema_name is None


@pytest.mark.parametrize(
    "config_text",
    [
        "article_limit: 0\n",
        "batch_size: 0\n",
        "database:\n  type: mysql\n",
        "database:\n  type: sqlite\n  url: sqlite:///data/test.db\n",
        "database:\n  type: postgresql\n  schema: corpus\n",
    ],
)
def test_load_invalid_persist_config_raises_service_error(
    tmp_path: Path,
    config_text: str,
) -> None:
    config_path = tmp_path / "persist.yaml"
    config_path.write_text(config_text, encoding="utf-8")

    with pytest.raises(ServiceError):
        ConfigurationService().load(config_path, PersistConfig)
