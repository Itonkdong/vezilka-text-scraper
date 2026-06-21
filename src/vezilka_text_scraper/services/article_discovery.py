"""Article discovery across Wikipedia categories."""

from __future__ import annotations

from collections import defaultdict, deque
from collections.abc import Iterator
from time import sleep
from typing import Protocol

from pydantic import BaseModel, ConfigDict

from vezilka_text_scraper.adapters.mediawiki import CategoryMember
from vezilka_text_scraper.services.scrape_config import ScrapeConfig
from vezilka_text_scraper.shared.exceptions import AdapterError, ServiceError
from vezilka_text_scraper.shared.logger import get_logger

LOGGER = get_logger(__name__)


class DiscoveredArticle(BaseModel):
    """A unique article discovered during category traversal."""

    model_config = ConfigDict(frozen=True)

    page_id: int
    title: str
    source_categories: list[str]


class CategoryMemberLister(Protocol):
    """Interface for listing MediaWiki category members."""

    def list_category_members(self, category: str, namespace: int) -> list[CategoryMember]:
        """Return direct page and subcategory members for a category."""


class ArticleDiscoveryService:
    """Discover unique Wikipedia articles from configured categories."""

    def __init__(self, mediawiki_adapter: CategoryMemberLister) -> None:
        self._mediawiki_adapter = mediawiki_adapter

    def discover(self, config: ScrapeConfig) -> list[DiscoveredArticle]:
        """Return unique articles discovered from the configured categories.

        Raises:
            ServiceError: If discovery fails and the config does not allow continuation.
        """
        source_categories_by_page_id: dict[int, set[str]] = defaultdict(set)
        title_by_page_id: dict[int, str] = {}

        for root_category in config.categories:
            per_category_count = 0
            visited_categories: set[str] = set()
            pending_categories: deque[tuple[str, int]] = deque([(root_category, 0)])

            while pending_categories and not self._global_limit_reached(
                title_by_page_id,
                self._effective_total_article_limit(config),
            ):
                category, depth = pending_categories.popleft()
                normalized_category = self._normalize_category_name(category)
                if normalized_category in visited_categories:
                    continue
                visited_categories.add(normalized_category)

                try:
                    members = self._mediawiki_adapter.list_category_members(
                        normalized_category,
                        namespace=config.namespace,
                    )
                except AdapterError as error:
                    if config.continue_on_error:
                        LOGGER.warning(f"Skipping category '{normalized_category}': {error}")
                        continue
                    raise ServiceError(f"Could not list category: {normalized_category}") from error

                for member in members:
                    if member.is_category:
                        self._queue_subcategory(member, depth, config, pending_categories)
                        continue

                    if (
                        config.per_category_article_limit is not None
                        and per_category_count >= config.per_category_article_limit
                    ):
                        continue
                    if self._global_limit_reached(
                        title_by_page_id,
                        self._effective_total_article_limit(config),
                    ):
                        break

                    is_new_for_root_category = (
                        root_category not in source_categories_by_page_id[member.page_id]
                    )
                    if member.page_id not in title_by_page_id:
                        title_by_page_id[member.page_id] = member.title
                    source_categories_by_page_id[member.page_id].add(root_category)
                    if is_new_for_root_category:
                        per_category_count += 1

                if config.request_delay_seconds > 0:
                    sleep(config.request_delay_seconds)

        return [
            DiscoveredArticle(
                page_id=page_id,
                title=title_by_page_id[page_id],
                source_categories=sorted(source_categories),
            )
            for page_id, source_categories in source_categories_by_page_id.items()
        ]

    def iter_discovered_articles(self, config: ScrapeConfig) -> Iterator[DiscoveredArticle]:
        """Yield unique articles as they are discovered from configured categories.

        This streaming path tracks visited categories and page ids, but a duplicate page
        reached later from another root category is skipped because the article may have
        already been fetched and written.
        """
        seen_page_ids: set[int] = set()

        for root_category in config.categories:
            per_category_count = 0
            visited_categories: set[str] = set()
            pending_categories: deque[tuple[str, int]] = deque([(root_category, 0)])

            while pending_categories and not self._global_limit_reached_for_seen(
                seen_page_ids,
                self._effective_total_article_limit(config),
            ):
                category, depth = pending_categories.popleft()
                normalized_category = self._normalize_category_name(category)
                if normalized_category in visited_categories:
                    continue
                visited_categories.add(normalized_category)

                try:
                    members = self._mediawiki_adapter.list_category_members(
                        normalized_category,
                        namespace=config.namespace,
                    )
                except AdapterError as error:
                    if config.continue_on_error:
                        LOGGER.warning(f"Skipping category '{normalized_category}': {error}")
                        continue
                    raise ServiceError(f"Could not list category: {normalized_category}") from error

                for member in members:
                    if member.is_category:
                        self._queue_subcategory(member, depth, config, pending_categories)
                        continue

                    if (
                        config.per_category_article_limit is not None
                        and per_category_count >= config.per_category_article_limit
                    ):
                        continue
                    if self._global_limit_reached_for_seen(
                        seen_page_ids,
                        self._effective_total_article_limit(config),
                    ):
                        break
                    if member.page_id in seen_page_ids:
                        continue

                    seen_page_ids.add(member.page_id)
                    per_category_count += 1
                    yield DiscoveredArticle(
                        page_id=member.page_id,
                        title=member.title,
                        source_categories=[root_category],
                    )

                if config.request_delay_seconds > 0:
                    sleep(config.request_delay_seconds)

    def _queue_subcategory(
        self,
        member: CategoryMember,
        depth: int,
        config: ScrapeConfig,
        pending_categories: deque[tuple[str, int]],
    ) -> None:
        if not config.recursive:
            return
        next_depth = depth + 1
        if next_depth > config.max_depth:
            return
        pending_categories.append((member.title, next_depth))

    def _global_limit_reached(
        self,
        title_by_page_id: dict[int, str],
        total_article_limit: int | None,
    ) -> bool:
        if total_article_limit is None:
            return False
        return len(title_by_page_id) >= total_article_limit

    def _global_limit_reached_for_seen(
        self,
        seen_page_ids: set[int],
        total_article_limit: int | None,
    ) -> bool:
        if total_article_limit is None:
            return False
        return len(seen_page_ids) >= total_article_limit

    def _effective_total_article_limit(self, config: ScrapeConfig) -> int | None:
        if config.per_category_article_limit is not None:
            return None
        return config.total_article_limit

    def _normalize_category_name(self, category: str) -> str:
        if category.startswith("Категорија:"):
            return category.removeprefix("Категорија:")
        if category.startswith("Category:"):
            return category.removeprefix("Category:")
        return category
