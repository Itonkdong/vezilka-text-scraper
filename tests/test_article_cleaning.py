from vezilka_text_scraper.models.article import RawArticleInput
from vezilka_text_scraper.services.article_cleaning import ArticleCleaningService
from vezilka_text_scraper.services.clean_config import CleanConfig
from vezilka_text_scraper.shared.constants import (
    SENSITIVITY_STATUS_CAUTION,
    SENSITIVITY_STATUS_RESTRICTED,
    SENSITIVITY_STATUS_SAFE,
)


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


def test_cleaning_removes_empty_parentheses_ranges() -> None:
    raw_wikitext = (
        "Александрин \"Алексин\" Пјетернела Франсоаз Тине ( - ), "
        "холандски истражувач на Африка и првата жена која пробала да ја премине Сахара."
    )
    config = CleanConfig(min_word_count=0, min_section_word_count=0)

    candidate = ArticleCleaningService().clean_article(
        _raw_article(raw_wikitext, title="Алексин Тине"),
        config,
        "2026-06-21T01:00:00+00:00",
    )

    assert "( - )" not in candidate.article.clean_text
    assert "Тине, холандски истражувач" in candidate.article.clean_text


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


def test_cleaning_removes_empty_list_items_and_latin_only_rows() -> None:
    raw_wikitext = """
Корисен македонски вовед кој треба да остане:
*
*
* PDF copy of select chapters
* Ewald, P. P., editor 50 Years of X-Ray Diffraction
* Македонска ставка
"""
    config = CleanConfig(min_word_count=0, min_section_word_count=0)

    candidate = ArticleCleaningService().clean_article(
        _raw_article(raw_wikitext, title="Учебници"),
        config,
        "2026-06-21T01:00:00+00:00",
    )

    assert "\n-\n" not in candidate.article.clean_text
    assert "PDF copy" not in candidate.article.clean_text
    assert "X-Ray Diffraction" not in candidate.article.clean_text
    assert "Корисен македонски вовед кој треба да остане." in candidate.article.clean_text
    assert "- Македонска ставка" in candidate.article.clean_text


def test_cleaning_normalizes_dangling_paragraph_punctuation() -> None:
    raw_wikitext = """
Оваа реченица завршува со остаток од отстранет список:
Оваа реченица завршува со остаток од отстранет дел,
Оваа реченица нема завршна интерпункција
"""
    config = CleanConfig(min_word_count=0, min_section_word_count=0)

    candidate = ArticleCleaningService().clean_article(
        _raw_article(raw_wikitext),
        config,
        "2026-06-21T01:00:00+00:00",
    )

    assert "список." in candidate.article.clean_text
    assert "дел." in candidate.article.clean_text
    assert "интерпункција." in candidate.article.clean_text
    assert "список:" not in candidate.article.clean_text
    assert "дел," not in candidate.article.clean_text


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


def test_cleaning_drops_rdf_code_sections() -> None:
    raw_wikitext = """
Вовед со корисна географска содржина која треба да остане во текстот.

== RDF-канали ==
Методот на RDF е утврден од Групата W3 и ги претставува информациите во облик на RDF-ознаки:
<rdf:RDF xmlns:rdf="" xmlns:geo="">
<>
<code> <>55.701</></code>
<code> <>12.552</></code>
<code></rdf:RDF></code>
"""
    config = CleanConfig(min_word_count=0, min_section_word_count=0)

    candidate = ArticleCleaningService().clean_article(
        _raw_article(raw_wikitext, title="Гео"),
        config,
        "2026-06-21T01:00:00+00:00",
    )

    assert [section.heading for section in candidate.article.sections] == ["Гео"]
    assert "RDF-канали" not in candidate.article.clean_text
    assert "<rdf:RDF" not in candidate.article.clean_text
    assert "<code>" not in candidate.article.clean_text


def test_cleaning_drops_html_code_sections() -> None:
    raw_wikitext = """
Вовед со доволно корисна содржина за географски поим.

== Микроформат ==
Микроформатот Geo овозможува координатите во HTML-страници да се означуваат
на начин што програмските алатки можат да ги „откриваат“. На пример:
<span class="geo">
<span class="latitude">50.167958</span>;
<span class="longitude">-97.133185</span>
</span>
што може да се прикаже како:
50.167958; -97.133185
"""
    config = CleanConfig(min_word_count=0, min_section_word_count=0)

    candidate = ArticleCleaningService().clean_article(
        _raw_article(raw_wikitext, title="Гео"),
        config,
        "2026-06-21T01:00:00+00:00",
    )

    assert [section.heading for section in candidate.article.sections] == ["Гео"]
    assert "Микроформат" not in candidate.article.clean_text
    assert "<span" not in candidate.article.clean_text
    assert "50.167958" not in candidate.article.clean_text


def test_cleaning_marks_safe_articles_without_sensitive_keywords() -> None:
    config = CleanConfig(min_word_count=0, min_section_word_count=0)

    candidate = ArticleCleaningService().clean_article(
        _raw_article("Географија е наука за Земјата и природните појави."),
        config,
        "2026-06-21T01:00:00+00:00",
    )

    assert candidate.article.sensitivity_status == SENSITIVITY_STATUS_SAFE
    assert candidate.article.sensitivity_keywords == []


def test_cleaning_marks_caution_articles_from_whole_article_text() -> None:
    config = CleanConfig(min_word_count=0, min_section_word_count=0)

    candidate = ArticleCleaningService().clean_article(
        _raw_article("Текстот ја спомнува Грција во географски контекст."),
        config,
        "2026-06-21T01:00:00+00:00",
    )

    assert candidate.article.sensitivity_status == SENSITIVITY_STATUS_CAUTION
    assert "грција" in candidate.article.sensitivity_keywords


def test_cleaning_marks_restricted_articles_from_whole_article_text() -> None:
    config = CleanConfig(min_word_count=0, min_section_word_count=0)

    candidate = ArticleCleaningService().clean_article(
        _raw_article("Овој текст содржи спор за името во телото на статијата."),
        config,
        "2026-06-21T01:00:00+00:00",
    )

    assert candidate.article.sensitivity_status == SENSITIVITY_STATUS_RESTRICTED
    assert "спор за името" in candidate.article.sensitivity_keywords
