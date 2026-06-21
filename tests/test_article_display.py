from vezilka_text_scraper.models.article import CleanedArticle, CleanedSection
from vezilka_text_scraper.services.article_display import ArticleDisplayService


def _cleaned_article(title: str = "Географија") -> CleanedArticle:
    return CleanedArticle(
        page_id=1,
        title=title,
        url="https://mk.wikipedia.org/wiki/Географија",
        language="mk",
        categories=["Категорија:Географија"],
        revision_id=10,
        last_modified="2026-01-01T00:00:00Z",
        scraped_at="2026-06-21T00:00:00+00:00",
        cleaned_at="2026-06-21T01:00:00+00:00",
        source_categories=["Географија"],
        clean_text="Географија\n\nГеографија е наука.",
        word_count=4,
        char_count=30,
        section_count=1,
        sections=[
            CleanedSection(
                heading="Географија",
                content="Географија е наука.\nОва е читлив текст.",
                word_count=7,
                char_count=36,
                position=0,
            )
        ],
    )


def test_display_service_formats_titles_sections_and_content() -> None:
    output = ArticleDisplayService().format_articles([_cleaned_article()])

    assert "Географија" in output
    assert "Географија е наука.\nОва е читлив текст." in output
    assert "\\n" not in output
    assert "clean_text" not in output
