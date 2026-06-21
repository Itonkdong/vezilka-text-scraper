"""MediaWiki API adapter."""

from __future__ import annotations

from collections.abc import MutableMapping
from time import sleep
from typing import Protocol, TypeAlias, cast
from urllib.parse import quote

import requests
from pydantic import BaseModel, ConfigDict

from vezilka_text_scraper.shared import env_variables
from vezilka_text_scraper.shared.constants import WIKIPEDIA_CANONICAL_BASE_URL
from vezilka_text_scraper.shared.exceptions import AdapterError

CATEGORY_NAMESPACE = 14
MEDIAWIKI_MAX_LIMIT = 500
JsonValue: TypeAlias = None | bool | int | float | str | list["JsonValue"] | dict[str, "JsonValue"]
JsonObject: TypeAlias = dict[str, JsonValue]


class MediaWikiResponse(Protocol):
    """HTTP response interface used by the MediaWiki adapter."""

    def raise_for_status(self) -> None:
        """Raise an HTTP error when the response status failed."""

    def json(self) -> JsonValue:
        """Return the decoded JSON response body."""


class MediaWikiSession(Protocol):
    """HTTP session interface used by the MediaWiki adapter."""

    @property
    def headers(self) -> MutableMapping[str, str]:
        """Return mutable request headers."""

    def get(self, url: str, params: dict[str, str | int], timeout: int) -> MediaWikiResponse:
        """Send a GET request."""


class CategoryMember(BaseModel):
    """A page or subcategory discovered from a Wikipedia category."""

    model_config = ConfigDict(frozen=True)

    page_id: int
    title: str
    namespace: int

    @property
    def is_category(self) -> bool:
        """Return whether the member is a category page."""
        return self.namespace == CATEGORY_NAMESPACE


class RawArticle(BaseModel):
    """Raw article payload returned by MediaWiki."""

    model_config = ConfigDict(frozen=True)

    page_id: int
    title: str
    url: str
    language: str
    categories: list[str]
    revision_id: int
    last_modified: str
    scraped_at: str
    source_categories: list[str]
    raw_wikitext: str


class MediaWikiAdapter:
    """Read category members and raw articles from the MediaWiki API."""

    def __init__(
        self,
        api_url: str = env_variables.MEDIAWIKI_API_URL,
        user_agent: str = env_variables.MEDIAWIKI_USER_AGENT,
        request_timeout_seconds: int = env_variables.MEDIAWIKI_REQUEST_TIMEOUT_SECONDS,
        max_retries: int = env_variables.MEDIAWIKI_MAX_RETRIES,
        session: MediaWikiSession | None = None,
    ) -> None:
        self._api_url = api_url
        self._request_timeout_seconds = request_timeout_seconds
        self._max_retries = max_retries
        self._session = session or requests.Session()
        self._session.headers.update({"User-Agent": user_agent})

    def list_category_members(self, category: str, namespace: int) -> list[CategoryMember]:
        """Return direct page and subcategory members for a Wikipedia category.

        Raises:
            AdapterError: If MediaWiki returns an invalid response or request fails.
        """
        members: list[CategoryMember] = []
        continuation: dict[str, str] = {}
        category_title = self._normalize_category_title(category)

        while True:
            params: dict[str, str | int] = {
                "action": "query",
                "list": "categorymembers",
                "cmtitle": category_title,
                "cmnamespace": f"{namespace}|{CATEGORY_NAMESPACE}",
                "cmlimit": MEDIAWIKI_MAX_LIMIT,
            }
            params.update(continuation)
            payload = self._get(params)
            query = self._get_mapping(payload, "query", "MediaWiki query response was invalid")
            raw_members = query.get("categorymembers", [])
            if not isinstance(raw_members, list):
                raise AdapterError("MediaWiki categorymembers response was not a list")

            for raw_member in raw_members:
                if not isinstance(raw_member, dict):
                    raise AdapterError("MediaWiki category member payload was invalid")
                member_payload = raw_member
                members.append(
                    CategoryMember(
                        page_id=self._get_int(member_payload, "pageid"),
                        title=self._get_str(member_payload, "title"),
                        namespace=self._get_int(member_payload, "ns"),
                    )
                )

            continuation_payload = payload.get("continue")
            if not isinstance(continuation_payload, dict):
                break
            continuation = {
                str(key): str(value)
                for key, value in continuation_payload.items()
            }

        return members

    def fetch_raw_article(
        self,
        page_id: int,
        language: str,
        source_categories: list[str],
        scraped_at: str,
        include_redirects: bool,
    ) -> RawArticle | None:
        """Return raw article wikitext and metadata for a page id.

        Raises:
            AdapterError: If MediaWiki returns an invalid response or request fails.
        """
        payload = self._get(
            {
                "action": "query",
                "prop": "info|revisions|categories",
                "pageids": page_id,
                "inprop": "url",
                "rvprop": "ids|timestamp|content",
                "rvslots": "main",
                "cllimit": MEDIAWIKI_MAX_LIMIT,
            }
        )
        query = self._get_mapping(payload, "query", "MediaWiki query response was invalid")
        pages = query.get("pages", {})
        if not isinstance(pages, dict):
            raise AdapterError("MediaWiki pages response was not a mapping")

        raw_page = pages.get(str(page_id))
        if not isinstance(raw_page, dict) or "missing" in raw_page:
            raise AdapterError(f"MediaWiki page was missing: {page_id}")
        page_payload = raw_page
        if "redirect" in page_payload and not include_redirects:
            return None

        revisions = page_payload.get("revisions", [])
        if not revisions:
            raise AdapterError(f"MediaWiki page had no revisions: {page_id}")
        if not isinstance(revisions, list):
            raise AdapterError(f"MediaWiki revisions payload was invalid: {page_id}")
        raw_revision = revisions[0]
        if not isinstance(raw_revision, dict):
            raise AdapterError(f"MediaWiki revision payload was invalid: {page_id}")
        revision_payload = raw_revision

        raw_wikitext = self._extract_revision_text(revision_payload)
        title = self._get_str(page_payload, "title")
        canonical_url = self._get_optional_str(page_payload, "canonicalurl") or self._canonical_url(
            title
        )

        return RawArticle(
            page_id=self._get_int(page_payload, "pageid"),
            title=title,
            url=canonical_url,
            language=language,
            categories=self._extract_categories(page_payload),
            revision_id=self._get_int(revision_payload, "revid"),
            last_modified=self._get_str(revision_payload, "timestamp"),
            scraped_at=scraped_at,
            source_categories=source_categories,
            raw_wikitext=raw_wikitext,
        )

    def _get(self, params: dict[str, str | int]) -> JsonObject:
        request_params = {"format": "json", **params}
        last_error: Exception | None = None

        for attempt in range(self._max_retries + 1):
            try:
                response = self._session.get(
                    self._api_url,
                    params=request_params,
                    timeout=self._request_timeout_seconds,
                )
                response.raise_for_status()
                payload = response.json()
                if not isinstance(payload, dict):
                    raise AdapterError("MediaWiki response was not a JSON object")
                if "error" in payload:
                    raise AdapterError(f"MediaWiki API error: {payload['error']}")
                return cast(JsonObject, payload)
            except AdapterError:
                raise
            except (requests.RequestException, ValueError) as error:
                last_error = error
                if attempt < self._max_retries:
                    sleep(0.2 * (attempt + 1))

        raise AdapterError("MediaWiki request failed") from last_error

    def _extract_revision_text(self, raw_revision: JsonObject) -> str:
        slots = raw_revision.get("slots", {})
        if isinstance(slots, dict):
            main_slot = slots.get("main", {})
            if isinstance(main_slot, dict):
                content = main_slot.get("*") or main_slot.get("content")
                if isinstance(content, str):
                    return content

        content = raw_revision.get("*")
        if isinstance(content, str):
            return content

        raise AdapterError("MediaWiki revision did not include raw wikitext")

    def _extract_categories(self, raw_page: JsonObject) -> list[str]:
        raw_categories = raw_page.get("categories", [])
        if not isinstance(raw_categories, list):
            return []
        return [
            str(category["title"])
            for category in raw_categories
            if isinstance(category, dict) and "title" in category
        ]

    def _get_mapping(self, payload: JsonObject, key: str, error_message: str) -> JsonObject:
        value = payload.get(key)
        if not isinstance(value, dict):
            raise AdapterError(error_message)
        return value

    def _get_str(self, payload: JsonObject, key: str) -> str:
        value = payload.get(key)
        if not isinstance(value, str):
            raise AdapterError(f"MediaWiki field '{key}' was not a string")
        return value

    def _get_optional_str(self, payload: JsonObject, key: str) -> str | None:
        value = payload.get(key)
        if value is None:
            return None
        if not isinstance(value, str):
            raise AdapterError(f"MediaWiki field '{key}' was not a string")
        return value

    def _get_int(self, payload: JsonObject, key: str) -> int:
        value = payload.get(key)
        if not isinstance(value, int):
            raise AdapterError(f"MediaWiki field '{key}' was not an integer")
        return value

    def _normalize_category_title(self, category: str) -> str:
        normalized_category = category.strip()
        if normalized_category.startswith("Категорија:") or normalized_category.startswith(
            "Category:"
        ):
            return normalized_category
        return f"Категорија:{normalized_category}"

    def _canonical_url(self, title: str) -> str:
        return f"{WIKIPEDIA_CANONICAL_BASE_URL}/{quote(title.replace(' ', '_'))}"
