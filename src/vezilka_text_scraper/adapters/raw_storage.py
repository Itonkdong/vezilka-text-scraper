"""Raw JSONL storage adapter."""

from __future__ import annotations

import json
from datetime import UTC, datetime
from pathlib import Path

from vezilka_text_scraper.adapters.mediawiki import RawArticle
from vezilka_text_scraper.shared import env_variables
from vezilka_text_scraper.shared.exceptions import AdapterError


class RawArticleJsonlStorageAdapter:
    """Persist raw article records as JSONL files."""

    def __init__(self, raw_data_dir: Path = env_variables.RAW_DATA_DIR) -> None:
        self._raw_data_dir = raw_data_dir

    def build_output_path(self, output_run_name: str | None) -> Path:
        """Return the JSONL output path for a scrape run."""
        file_name = output_run_name or f"wiki_raw_{self._timestamp()}.jsonl"
        return self._raw_data_dir / file_name

    def write_articles(self, articles: list[RawArticle], output_path: Path) -> int:
        """Write raw article records to a JSONL file.

        Raises:
            AdapterError: If the output file cannot be written.
        """
        try:
            output_path.parent.mkdir(parents=True, exist_ok=True)
            with output_path.open("w", encoding="utf-8") as output_file:
                for article in articles:
                    output_file.write(
                        json.dumps(article.model_dump(), ensure_ascii=False, sort_keys=True)
                    )
                    output_file.write("\n")
        except OSError as error:
            raise AdapterError(f"Could not write raw JSONL file: {output_path}") from error

        return len(articles)

    def _timestamp(self) -> str:
        return datetime.now(UTC).strftime("%Y%m%d_%H%M%S")
