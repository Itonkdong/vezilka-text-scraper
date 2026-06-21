"""MediaWiki article cleaning services."""

from __future__ import annotations

import re

import mwparserfromhell
from mwparserfromhell.nodes import Tag, Template
from pydantic import BaseModel, ConfigDict, Field

from vezilka_text_scraper.models.article import CleanedArticle, CleanedSection, RawArticleInput
from vezilka_text_scraper.services.clean_config import CleanConfig
from vezilka_text_scraper.shared.constants import (
    DISAMBIGUATION_TITLE_MARKERS,
    STOP_SECTION_TITLES,
)
from vezilka_text_scraper.shared.exceptions import ServiceError

SECTION_PATTERN = re.compile(r"^(={2,6})\s*(.*?)\s*\1\s*$", re.MULTILINE)
CITATION_MARKER_PATTERN = re.compile(r"\[\d+]|\[citation needed]", re.IGNORECASE)
WHITESPACE_PATTERN = re.compile(r"[ \t]+")
BLANK_LINES_PATTERN = re.compile(r"\n{3,}")


class CleanedArticleCandidate(BaseModel):
    """Cleaned article before quality filters are applied."""

    model_config = ConfigDict(frozen=True)

    article: CleanedArticle
    word_count: int = Field(ge=0)


class RawSection(BaseModel):
    """Raw article section before MediaWiki markup cleaning."""

    model_config = ConfigDict(frozen=True)

    heading: str
    content: str


class ArticleCleaningService:
    """Clean raw MediaWiki article records into readable article text and sections."""

    def clean_article(
        self,
        article: RawArticleInput,
        config: CleanConfig,
        cleaned_at: str,
    ) -> CleanedArticleCandidate:
        """Return a cleaned article candidate with section and article statistics.

        Raises:
            ServiceError: If the raw article cannot be cleaned.
        """
        try:
            cleaned_sections = self._clean_sections(article, config)
        except Exception as error:
            raise ServiceError(f"Could not clean article '{article.title}'") from error

        clean_text = self._build_clean_text(article.title, cleaned_sections)
        word_count = self._count_words(clean_text)
        cleaned_article = CleanedArticle(
            page_id=article.page_id,
            title=article.title,
            url=article.url,
            language=article.language,
            categories=article.categories,
            revision_id=article.revision_id,
            last_modified=article.last_modified,
            scraped_at=article.scraped_at,
            cleaned_at=cleaned_at,
            source_categories=article.source_categories,
            clean_text=clean_text,
            word_count=word_count,
            char_count=len(clean_text),
            section_count=len(cleaned_sections),
            sections=cleaned_sections,
        )
        return CleanedArticleCandidate(article=cleaned_article, word_count=word_count)

    def should_skip_article(self, candidate: CleanedArticleCandidate, config: CleanConfig) -> bool:
        """Return whether a cleaned article should be excluded from processed output."""
        if candidate.word_count < config.min_word_count:
            return True
        return config.skip_disambiguation_pages and self._is_disambiguation_title(
            candidate.article.title
        )

    def _clean_sections(
        self,
        article: RawArticleInput,
        config: CleanConfig,
    ) -> list[CleanedSection]:
        raw_sections = self._extract_raw_sections(article.title, article.raw_wikitext)
        cleaned_sections: list[CleanedSection] = []

        for raw_section in raw_sections:
            normalized_heading = self._normalize_heading(raw_section.heading)
            if (
                config.remove_navigation_sections
                and normalized_heading in STOP_SECTION_TITLES
            ):
                continue

            cleaned_content = self._clean_wikitext(raw_section.content, config)
            if not cleaned_content:
                continue

            position = len(cleaned_sections)
            cleaned_sections.append(
                CleanedSection(
                    heading=normalized_heading,
                    content=cleaned_content,
                    word_count=self._count_words(cleaned_content),
                    char_count=len(cleaned_content),
                    position=position,
                )
            )

        return cleaned_sections

    def _extract_raw_sections(self, title: str, raw_wikitext: str) -> list[RawSection]:
        matches = list(SECTION_PATTERN.finditer(raw_wikitext))
        if not matches:
            return [RawSection(heading=title, content=raw_wikitext)]

        sections: list[RawSection] = [
            RawSection(heading=title, content=raw_wikitext[: matches[0].start()])
        ]
        for index, match in enumerate(matches):
            next_start = (
                matches[index + 1].start()
                if index + 1 < len(matches)
                else len(raw_wikitext)
            )
            sections.append(
                RawSection(
                    heading=match.group(2),
                    content=raw_wikitext[match.end() : next_start],
                )
            )
        return sections

    def _clean_wikitext(self, raw_wikitext: str, config: CleanConfig) -> str:
        working_text = raw_wikitext
        if config.remove_tables:
            working_text = self._remove_tables(working_text)

        wikicode = mwparserfromhell.parse(working_text)
        if config.remove_references:
            self._remove_references(wikicode)
        if config.remove_templates:
            self._remove_templates(wikicode)
        if config.remove_files:
            self._remove_file_links(wikicode)
        if config.remove_categories:
            self._remove_category_links(wikicode)
        if config.remove_external_links:
            self._replace_external_links(wikicode)

        self._replace_wiki_links(wikicode)
        cleaned_text = wikicode.strip_code(normalize=True, collapse=True)
        cleaned_text = CITATION_MARKER_PATTERN.sub("", cleaned_text)
        if config.normalize_whitespace:
            cleaned_text = self._normalize_whitespace(cleaned_text)
        return cleaned_text.strip()

    def _remove_tables(self, text: str) -> str:
        lines = text.splitlines()
        kept_lines: list[str] = []
        table_depth = 0
        for line in lines:
            stripped_line = line.strip()
            if stripped_line.startswith("{|"):
                table_depth += 1
                continue
            if table_depth > 0:
                if stripped_line.startswith("|}"):
                    table_depth -= 1
                continue
            kept_lines.append(line)
        return "\n".join(kept_lines)

    def _remove_references(self, wikicode: mwparserfromhell.wikicode.Wikicode) -> None:
        for tag in list(wikicode.filter_tags(recursive=True)):
            if self._is_reference_tag(tag):
                wikicode.remove(tag)

    def _remove_templates(self, wikicode: mwparserfromhell.wikicode.Wikicode) -> None:
        for template in list(wikicode.filter_templates(recursive=True)):
            self._safe_remove(wikicode, template)

    def _remove_file_links(self, wikicode: mwparserfromhell.wikicode.Wikicode) -> None:
        for wikilink in list(wikicode.filter_wikilinks(recursive=True)):
            title = str(wikilink.title).strip()
            if title.startswith(("Податотека:", "File:", "Image:", "Слика:")):
                wikicode.remove(wikilink)

    def _remove_category_links(self, wikicode: mwparserfromhell.wikicode.Wikicode) -> None:
        for wikilink in list(wikicode.filter_wikilinks(recursive=True)):
            title = str(wikilink.title).strip()
            if title.startswith(("Категорија:", "Category:")):
                wikicode.remove(wikilink)

    def _replace_external_links(self, wikicode: mwparserfromhell.wikicode.Wikicode) -> None:
        for external_link in list(wikicode.filter_external_links(recursive=True)):
            replacement = ""
            if external_link.title is not None:
                replacement = str(external_link.title).strip()
            wikicode.replace(external_link, replacement)

    def _replace_wiki_links(self, wikicode: mwparserfromhell.wikicode.Wikicode) -> None:
        for wikilink in list(wikicode.filter_wikilinks(recursive=True)):
            title = str(wikilink.title).strip()
            if title.startswith(
                ("Категорија:", "Category:", "Податотека:", "File:", "Image:", "Слика:")
            ):
                wikicode.remove(wikilink)
                continue
            replacement = str(wikilink.text or wikilink.title).strip()
            wikicode.replace(wikilink, replacement)

    def _safe_remove(
        self,
        wikicode: mwparserfromhell.wikicode.Wikicode,
        template: Template,
    ) -> None:
        try:
            wikicode.remove(template)
        except ValueError:
            return

    def _is_reference_tag(self, tag: Tag) -> bool:
        return str(tag.tag).strip().lower() in {"ref", "references"}

    def _normalize_heading(self, heading: str) -> str:
        return WHITESPACE_PATTERN.sub(" ", heading.strip())

    def _normalize_whitespace(self, text: str) -> str:
        lines = [WHITESPACE_PATTERN.sub(" ", line).strip() for line in text.splitlines()]
        text_without_trailing_spaces = "\n".join(line for line in lines if line)
        return BLANK_LINES_PATTERN.sub("\n\n", text_without_trailing_spaces)

    def _build_clean_text(self, title: str, sections: list[CleanedSection]) -> str:
        parts = [title.strip()]
        for section in sections:
            if section.heading != title:
                parts.append(section.heading)
            parts.append(section.content)
        return "\n\n".join(part for part in parts if part.strip()).strip()

    def _count_words(self, text: str) -> int:
        return len([word for word in re.split(r"\s+", text.strip()) if word])

    def _is_disambiguation_title(self, title: str) -> bool:
        normalized_title = title.lower()
        return any(marker in normalized_title for marker in DISAMBIGUATION_TITLE_MARKERS)
