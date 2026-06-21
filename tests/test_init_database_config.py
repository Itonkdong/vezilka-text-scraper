from pathlib import Path

import pytest

from vezilka_text_scraper.services.configuration import ConfigurationService
from vezilka_text_scraper.services.init_database_config import InitDatabaseConfig
from vezilka_text_scraper.shared import env_variables


def test_load_init_database_config(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(env_variables, "SQLITE_DATABASE_PATH", Path("data/test.db"))
    config_path = tmp_path / "init_database.yaml"
    config_path.write_text(
        """
database:
  type: sqlite
""",
        encoding="utf-8",
    )

    config = ConfigurationService().load(config_path, InitDatabaseConfig)

    assert config.database.type == "sqlite"
    assert config.database.url == "sqlite:///data/test.db"
    assert config.database.schema_name is None
