from vezilka_text_scraper.models.article import RawArticleInput
from vezilka_text_scraper.services.article_cleaning import ArticleCleaningService
from vezilka_text_scraper.services.clean_config import CleanConfig


def _raw_article(raw_wikitext: str, title: str = "Географија") -> RawArticleInput:
    return RawArticleInput(
        page_id=1,
        title=title,
        url="https://mk.wikipedia.org/wiki/Географија",
        language="mk",
        categories=["Категорија:Географија"],
        revision_id=10,
        last_modified="2026-01-01T00:00:00Z",
        scraped_at="2026-06-21T00:00:00+00:00",
        source_categories=["Географија"],
        raw_wikitext=raw_wikitext,
    )


def test_cleaning_removes_wiki_noise_and_keeps_visible_text() -> None:
    raw_wikitext = """
{{Без извори}}
[[Податотека:Map.jpg|thumb|Карта]]
'''Географија'''<ref>извор</ref> е [[наука|научна област]].
[https://example.com видлив текст] [https://example.com]
[[Категорија:Географија]]
{| class="wikitable"
|+ Табела
|-
| вредност
|}
"""
    config = CleanConfig(min_word_count=0)

    candidate = ArticleCleaningService().clean_article(
        _raw_article(raw_wikitext),
        config,
        "2026-06-21T01:00:00+00:00",
    )

    assert "Без извори" not in candidate.article.clean_text
    assert "Податотека" not in candidate.article.clean_text
    assert "извор" not in candidate.article.clean_text
    assert "Категорија" not in candidate.article.clean_text
    assert "вредност" not in candidate.article.clean_text
    assert "научна област" in candidate.article.clean_text
    assert "видлив текст" in candidate.article.clean_text
    assert "https://example.com" not in candidate.article.clean_text


def test_cleaning_extracts_sections_and_removes_navigation_sections() -> None:
    raw_wikitext = """
Воведна реченица.

== Историја ==
Историска содржина.

== Наводи ==
* непотребен извор
"""
    config = CleanConfig(min_word_count=0)

    candidate = ArticleCleaningService().clean_article(
        _raw_article(raw_wikitext),
        config,
        "2026-06-21T01:00:00+00:00",
    )

    assert [section.heading for section in candidate.article.sections] == ["Географија", "Историја"]
    assert candidate.article.sections[0].content == "Воведна реченица."
    assert "Наводи" not in candidate.article.clean_text
    assert candidate.article.section_count == 2


def test_cleaning_filter_skips_short_and_disambiguation_articles() -> None:
    service = ArticleCleaningService()
    config = CleanConfig(min_word_count=10, skip_disambiguation_pages=True)
    short_candidate = service.clean_article(
        _raw_article("Краток текст."),
        config,
        "2026-06-21T01:00:00+00:00",
    )
    disambiguation_candidate = service.clean_article(
        _raw_article("Ова е доволно долг текст за тестирање на филтерот.", "Скопје (појаснување)"),
        CleanConfig(min_word_count=0, skip_disambiguation_pages=True),
        "2026-06-21T01:00:00+00:00",
    )

    assert service.should_skip_article(short_candidate, config) is True
    assert (
        service.should_skip_article(
            disambiguation_candidate,
            CleanConfig(min_word_count=0, skip_disambiguation_pages=True),
        )
        is True
    )
