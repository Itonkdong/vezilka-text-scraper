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
    config = CleanConfig(min_word_count=0, min_section_word_count=0)

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

== Литература ==
* книга

== Дополнителна литература ==
* уште една книга

== Поврзано ==
* Ерупција
* Видови на вулкански избув
* Тектоника на плочите
* Показател на вулканска избувност
"""
    config = CleanConfig(min_word_count=0, min_section_word_count=0)

    candidate = ArticleCleaningService().clean_article(
        _raw_article(raw_wikitext),
        config,
        "2026-06-21T01:00:00+00:00",
    )

    assert [section.heading for section in candidate.article.sections] == ["Географија", "Историја"]
    assert candidate.article.sections[0].content == "Воведна реченица."
    assert "Наводи" not in candidate.article.clean_text
    assert "Литература" not in candidate.article.clean_text
    assert "Дополнителна литература" not in candidate.article.clean_text
    assert "Поврзано" not in candidate.article.clean_text
    assert "уште една книга" not in candidate.article.clean_text
    assert "Тектоника на плочите" not in candidate.article.clean_text
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
    assert service.get_skip_reason(short_candidate, config) == (
        "word count 1 is below minimum 10"
    )
    assert (
        service.should_skip_article(
            disambiguation_candidate,
            CleanConfig(min_word_count=0, skip_disambiguation_pages=True),
        )
        is True
    )
    assert (
        service.get_skip_reason(
            disambiguation_candidate,
            CleanConfig(min_word_count=0, skip_disambiguation_pages=True),
        )
        == "title looks like a disambiguation page"
    )


def test_cleaning_removes_intro_etymology_explanations() -> None:
    raw_wikitext = (
        "'''Географија''' (од [[старогрчки]]: γεω „земја“ и γραφία „опишува“) "
        "или [[земјопис]] — описна наука за планетата Земја."
    )
    config = CleanConfig(min_word_count=0, min_section_word_count=0)

    candidate = ArticleCleaningService().clean_article(
        _raw_article(raw_wikitext),
        config,
        "2026-06-21T01:00:00+00:00",
    )

    assert "старогрчки" not in candidate.article.clean_text
    assert "γεω" not in candidate.article.clean_text
    assert "γραφία" not in candidate.article.clean_text
    assert "Географија или земјопис" in candidate.article.clean_text


def test_cleaning_keeps_list_items_with_dash_markers() -> None:
    raw_wikitext = """
Во географијата постојат повеќе полиња:
* физичка географија
* антропогеографија
# картографија
# геодезија
"""
    config = CleanConfig(min_word_count=0, min_section_word_count=0)

    candidate = ArticleCleaningService().clean_article(
        _raw_article(raw_wikitext),
        config,
        "2026-06-21T01:00:00+00:00",
    )

    assert "- физичка географија" in candidate.article.clean_text
    assert "- антропогеографија" in candidate.article.clean_text
    assert "- картографија" in candidate.article.clean_text
    assert "- геодезија" in candidate.article.clean_text


def test_cleaning_skips_sections_below_minimum_word_count() -> None:
    raw_wikitext = """
Воведна содржина со доволно зборови за да остане како корисен текст.

== Некои од најголемите вулкани во светот ==
* Сѐ уште активни
{| class="wikitable"
! Вулкан !! Височина !! Место
|-
| Котопакси || 5897 м || Еквадор
|}

== Создавање на вулкани ==
Вулканите се места од каде што излегува вжарен карпест материјал од внатрешноста на земјата.
"""
    config = CleanConfig(min_word_count=0, min_section_word_count=10)

    candidate = ArticleCleaningService().clean_article(
        _raw_article(raw_wikitext, title="Вулкан"),
        config,
        "2026-06-21T01:00:00+00:00",
    )

    section_headings = [section.heading for section in candidate.article.sections]
    assert "Некои од најголемите вулкани во светот" not in section_headings
    assert "Сѐ уште активни" not in candidate.article.clean_text
    assert section_headings == ["Вулкан", "Создавање на вулкани"]


def test_cleaning_drops_sections_that_are_only_table_preambles() -> None:
    raw_wikitext = """
Почнувајќи од Северниот Пол и упатувајќи се кон југ до Јужниот Пол,
115. западен меридијан поминува низ:
{| class="wikitable plainrowheaders"
! scope="col" width="130" | Координати
! scope="col" | Држава, територија или море
! scope="col" | Белешки
|-
| style="background:#b0e0e6;" |
! scope="row" style="background:#b0e0e6;" | Северноледен Океан
| style="background:#b0e0e6;" |
|-
|
! scope="row" |
| Северозападни Територии — Броков Остров
|-
| style="background:#b0e0e6;" |
! scope="row" style="background:#b0e0e6;" | Тихи Океан
| style="background:#b0e0e6;" | Западно од Кларион
|-
|}
"""
    config = CleanConfig(min_word_count=0, min_section_word_count=0)

    candidate = ArticleCleaningService().clean_article(
        _raw_article(raw_wikitext, title="115. западен меридијан"),
        config,
        "2026-06-21T01:00:00+00:00",
    )

    assert candidate.article.sections == []
    assert "поминува низ" not in candidate.article.clean_text
    assert "Северноледен Океан" not in candidate.article.clean_text
