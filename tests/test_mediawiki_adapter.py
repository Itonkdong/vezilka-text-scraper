from typing import Any

from vezilka_text_scraper.adapters.mediawiki import MediaWikiAdapter


class FakeResponse:
    def __init__(self, payload: dict[str, Any]) -> None:
        self._payload = payload

    def raise_for_status(self) -> None:
        return None

    def json(self) -> dict[str, Any]:
        return self._payload


class FakeSession:
    def __init__(self, responses: list[dict[str, Any]]) -> None:
        self.headers: dict[str, str] = {}
        self.responses = responses
        self.requests: list[dict[str, Any]] = []

    def get(self, url: str, params: dict[str, Any], timeout: int) -> FakeResponse:
        self.requests.append({"url": url, "params": params, "timeout": timeout})
        return FakeResponse(self.responses.pop(0))


def test_mediawiki_adapter_lists_category_members() -> None:
    session = FakeSession(
        [
            {
                "query": {
                    "categorymembers": [
                        {"pageid": 1, "title": "Article", "ns": 0},
                        {"pageid": 2, "title": "Категорија:Реки", "ns": 14},
                    ]
                }
            }
        ]
    )
    adapter = MediaWikiAdapter(
        api_url="https://example.test/api.php",
        user_agent="test-agent",
        session=session,
    )

    members = adapter.list_category_members("Географија", namespace=0)

    assert [member.page_id for member in members] == [1, 2]
    assert session.headers["User-Agent"] == "test-agent"
    assert session.requests[0]["params"]["cmtitle"] == "Категорија:Географија"


def test_mediawiki_adapter_passes_continuation_tokens() -> None:
    session = FakeSession(
        [
            {
                "query": {"categorymembers": [{"pageid": 1, "title": "Article A", "ns": 0}]},
                "continue": {"cmcontinue": "page|next", "continue": "-||"},
            },
            {
                "query": {"categorymembers": [{"pageid": 2, "title": "Article B", "ns": 0}]},
            },
        ]
    )
    adapter = MediaWikiAdapter(api_url="https://example.test/api.php", session=session)

    members = adapter.list_category_members("Географија", namespace=0)

    assert [member.page_id for member in members] == [1, 2]
    assert session.requests[1]["params"]["cmcontinue"] == "page|next"
    assert session.requests[1]["params"]["continue"] == "-||"


def test_mediawiki_adapter_fetches_raw_article() -> None:
    session = FakeSession(
        [
            {
                "query": {
                    "pages": {
                        "1": {
                            "pageid": 1,
                            "title": "Македонија",
                            "canonicalurl": "https://mk.wikipedia.org/wiki/Македонија",
                            "categories": [{"title": "Категорија:Географија"}],
                            "revisions": [
                                {
                                    "revid": 10,
                                    "timestamp": "2024-01-01T00:00:00Z",
                                    "slots": {"main": {"*": "raw text"}},
                                }
                            ],
                        }
                    }
                }
            }
        ]
    )
    adapter = MediaWikiAdapter(api_url="https://example.test/api.php", session=session)

    article = adapter.fetch_raw_article(
        page_id=1,
        language="mk",
        source_categories=["Географија"],
        scraped_at="2026-01-01T00:00:00+00:00",
        include_redirects=False,
    )

    assert article is not None
    assert article.page_id == 1
    assert article.revision_id == 10
    assert article.raw_wikitext == "raw text"
