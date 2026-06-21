"""JSONL adapters for raw and cleaned article files."""

from __future__ import annotations

import json
from datetime import UTC, datetime
from pathlib import Path

from pydantic import ValidationError

from vezilka_text_scraper.models.article import CleanedArticle, RawArticleInput
from vezilka_text_scraper.shared import env_variables
from vezilka_text_scraper.shared.exceptions import AdapterError


class RawArticleJsonlReader:
    """Read raw scraper records from JSONL files."""

    def __init__(self, raw_data_dir: Path = env_variables.RAW_DATA_DIR) -> None:
        self._raw_data_dir = raw_data_dir

    def resolve_input_path(self, input_path: Path | None) -> Path:
        """Return the configured input path or newest raw JSONL file."""
        if input_path is not None:
            if not input_path.exists():
                raise AdapterError(f"Raw input file does not exist: {input_path}")
            return input_path

        candidates = sorted(
            self._raw_data_dir.glob("*.jsonl"),
            key=lambda path: path.stat().st_mtime,
            reverse=True,
        )
        if not candidates:
            raise AdapterError(f"No raw JSONL files found in {self._raw_data_dir}")
        return candidates[0]

    def read_articles(self, input_path: Path) -> list[RawArticleInput]:
        """Read raw article records from a JSONL file.

        Raises:
            AdapterError: If the file cannot be read or records are invalid.
        """
        articles: list[RawArticleInput] = []
        try:
            with input_path.open(encoding="utf-8") as input_file:
                for line_number, line in enumerate(input_file, start=1):
                    stripped_line = line.strip()
                    if not stripped_line:
                        continue
                    try:
                        payload = json.loads(stripped_line)
                        articles.append(RawArticleInput(**payload))
                    except (json.JSONDecodeError, ValidationError) as error:
                        raise AdapterError(
                            f"Invalid raw article record at {input_path}:{line_number}"
                        ) from error
        except OSError as error:
            raise AdapterError(f"Could not read raw JSONL file: {input_path}") from error

        return articles


class CleanedArticleJsonlWriter:
    """Write cleaned article records to processed JSONL files."""

    def __init__(self, processed_data_dir: Path = env_variables.PROCESSED_DATA_DIR) -> None:
        self._processed_data_dir = processed_data_dir

    def build_output_path(self, output_run_name: str | None) -> Path:
        """Return the processed JSONL output path for a clean run."""
        file_name = output_run_name or f"wiki_clean_{self._timestamp()}.jsonl"
        return self._processed_data_dir / file_name

    def write_articles(self, articles: list[CleanedArticle], output_path: Path) -> int:
        """Write cleaned article records to a JSONL file.

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
            raise AdapterError(f"Could not write processed JSONL file: {output_path}") from error

        return len(articles)

    def _timestamp(self) -> str:
        return datetime.now(UTC).strftime("%Y%m%d_%H%M%S")


class CleanedArticleJsonlReader:
    """Read cleaned article records from processed JSONL files."""

    def __init__(self, processed_data_dir: Path = env_variables.PROCESSED_DATA_DIR) -> None:
        self._processed_data_dir = processed_data_dir

    def resolve_input_path(self, input_path: Path | None) -> Path:
        """Return the configured input path or newest processed JSONL file."""
        if input_path is not None:
            if not input_path.exists():
                raise AdapterError(f"Processed input file does not exist: {input_path}")
            return input_path

        candidates = sorted(
            self._processed_data_dir.glob("*.jsonl"),
            key=lambda path: path.stat().st_mtime,
            reverse=True,
        )
        if not candidates:
            raise AdapterError(f"No processed JSONL files found in {self._processed_data_dir}")
        return candidates[0]

    def read_articles(
        self,
        input_path: Path,
        article_limit: int | None,
    ) -> list[CleanedArticle]:
        """Read cleaned article records from a JSONL file.

        Raises:
            AdapterError: If the file cannot be read or records are invalid.
        """
        articles: list[CleanedArticle] = []
        try:
            with input_path.open(encoding="utf-8") as input_file:
                for line_number, line in enumerate(input_file, start=1):
                    if article_limit is not None and len(articles) >= article_limit:
                        break
                    stripped_line = line.strip()
                    if not stripped_line:
                        continue
                    try:
                        payload = json.loads(stripped_line)
                        articles.append(CleanedArticle(**payload))
                    except (json.JSONDecodeError, ValidationError) as error:
                        raise AdapterError(
                            f"Invalid cleaned article record at {input_path}:{line_number}"
                        ) from error
        except OSError as error:
            raise AdapterError(f"Could not read processed JSONL file: {input_path}") from error

        return articles
