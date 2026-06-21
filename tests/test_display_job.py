import json
from pathlib import Path

from pytest import CaptureFixture

from vezilka_text_scraper.adapters.article_jsonl import CleanedArticleJsonlReader
from vezilka_text_scraper.jobs.display import WikipediaDisplayJob
from vezilka_text_scraper.services.article_display import ArticleDisplayService
from vezilka_text_scraper.services.configuration import ConfigurationService


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
        "clean_text": f"{title}\n\nСодржина.",
        "word_count": 2,
        "char_count": 10,
        "section_count": 1,
        "sections": [
            {
                "heading": title,
                "content": "Содржина.",
                "word_count": 1,
                "char_count": 9,
                "position": 0,
            }
        ],
    }


def test_display_job_prints_limited_articles(
    tmp_path: Path,
    capsys: CaptureFixture[str],
) -> None:
    processed_dir = tmp_path / "processed"
    processed_dir.mkdir()
    input_path = processed_dir / "processed.jsonl"
    input_path.write_text(
        "\n".join(
            [
                json.dumps(_processed_record(1, "Прва"), ensure_ascii=False),
                json.dumps(_processed_record(2, "Втора"), ensure_ascii=False),
            ]
        ),
        encoding="utf-8",
    )
    config_path = tmp_path / "display.yaml"
    config_path.write_text(
        f"""
input_path: {input_path}
article_limit: 1
""",
        encoding="utf-8",
    )
    job = WikipediaDisplayJob(
        configuration_service=ConfigurationService(),
        reader=CleanedArticleJsonlReader(processed_dir),
        display_service=ArticleDisplayService(),
    )

    result = job.run(config_path)
    captured = capsys.readouterr()

    assert result.displayed_count == 1
    assert "Прва" in captured.out
    assert "Втора" not in captured.out
