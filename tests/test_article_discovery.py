from vezilka_text_scraper.adapters.mediawiki import CategoryMember
from vezilka_text_scraper.services.article_discovery import ArticleDiscoveryService
from vezilka_text_scraper.services.scrape_config import ScrapeConfig


class FakeMediaWikiAdapter:
    def __init__(self, members_by_category: dict[str, list[CategoryMember]]) -> None:
        self.members_by_category = members_by_category
        self.calls: list[str] = []

    def list_category_members(self, category: str, namespace: int) -> list[CategoryMember]:
        self.calls.append(category)
        return self.members_by_category.get(category, [])


def test_discovery_respects_recursive_depth_and_avoids_loops() -> None:
    adapter = FakeMediaWikiAdapter(
        {
            "Географија": [
                CategoryMember(page_id=100, title="Article A", namespace=0),
                CategoryMember(page_id=200, title="Категорија:Реки", namespace=14),
            ],
            "Реки": [
                CategoryMember(page_id=101, title="Article B", namespace=0),
                CategoryMember(page_id=201, title="Категорија:Географија", namespace=14),
            ],
        }
    )
    config = ScrapeConfig(
        categories=["Географија"],
        recursive=True,
        max_depth=1,
        request_delay_seconds=0,
    )

    articles = ArticleDiscoveryService(adapter).discover(config)

    assert [article.page_id for article in articles] == [100, 101]
    assert adapter.calls == ["Географија", "Реки"]


def test_discovery_respects_article_caps_and_deduplicates() -> None:
    adapter = FakeMediaWikiAdapter(
        {
            "Географија": [
                CategoryMember(page_id=100, title="Article A", namespace=0),
                CategoryMember(page_id=101, title="Article B", namespace=0),
                CategoryMember(page_id=102, title="Article C", namespace=0),
            ],
            "Историја": [
                CategoryMember(page_id=100, title="Article A", namespace=0),
                CategoryMember(page_id=103, title="Article D", namespace=0),
            ],
        }
    )
    config = ScrapeConfig(
        categories=["Географија", "Историја"],
        recursive=False,
        total_article_limit=3,
        per_category_article_limit=2,
        request_delay_seconds=0,
    )

    articles = ArticleDiscoveryService(adapter).discover(config)

    assert [article.page_id for article in articles] == [100, 101, 103]
    assert articles[0].source_categories == ["Географија", "Историја"]


def test_per_category_limit_overrides_global_limit() -> None:
    adapter = FakeMediaWikiAdapter(
        {
            "Географија": [
                CategoryMember(page_id=100, title="Article A", namespace=0),
                CategoryMember(page_id=101, title="Article B", namespace=0),
            ],
            "Историја": [
                CategoryMember(page_id=102, title="Article C", namespace=0),
                CategoryMember(page_id=103, title="Article D", namespace=0),
            ],
        }
    )
    config = ScrapeConfig(
        categories=["Географија", "Историја"],
        recursive=False,
        total_article_limit=1,
        per_category_article_limit=2,
        request_delay_seconds=0,
    )

    articles = ArticleDiscoveryService(adapter).discover(config)

    assert [article.page_id for article in articles] == [100, 101, 102, 103]
