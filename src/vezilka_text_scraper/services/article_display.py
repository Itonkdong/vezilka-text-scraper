"""Readable console formatting for cleaned articles."""

from vezilka_text_scraper.models.article import CleanedArticle


class ArticleDisplayService:
    """Format cleaned articles for human-readable console inspection."""

    def format_articles(self, articles: list[CleanedArticle]) -> str:
        """Return article titles, section headings, and section text for display."""
        return "\n\n".join(self._format_article(article) for article in articles)

    def _format_article(self, article: CleanedArticle) -> str:
        lines = [
            "=" * 100,
            article.title,
            "=" * 100,
        ]
        for section in article.sections:
            lines.extend(
                [
                    "",
                    section.heading,
                    "-" * len(section.heading),
                    section.content,
                ]
            )
        return "\n".join(lines).strip()
