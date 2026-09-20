from __future__ import annotations

import asyncio
import json
import urllib.error
import urllib.parse
import urllib.request
from dataclasses import dataclass


class SearchProviderError(RuntimeError):
    pass


class _NoRedirectHandler(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        return None


@dataclass(frozen=True, slots=True)
class SearchResult:
    url: str
    title: str
    snippet: str


class BraveSearchProvider:
    endpoint = "https://api.search.brave.com/res/v1/web/search"

    def __init__(self, api_key: str, *, max_results: int = 10):
        self._api_key = api_key
        self._max_results = min(max(max_results, 1), 20)

    async def search(self, query: str) -> list[SearchResult]:
        return await asyncio.to_thread(self._search_sync, query)

    def _search_sync(self, query: str) -> list[SearchResult]:
        params = urllib.parse.urlencode({"q": query, "count": self._max_results, "country": "br"})
        request = urllib.request.Request(
            f"{self.endpoint}?{params}",
            headers={
                "Accept": "application/json",
                "X-Subscription-Token": self._api_key,
                "User-Agent": "SignalPrice/0.1 discovery-candidates",
            },
        )
        try:
            opener = urllib.request.build_opener(_NoRedirectHandler())
            with opener.open(request, timeout=10) as response:
                raw = response.read(1_000_001)
                if len(raw) > 1_000_000:
                    raise SearchProviderError("the search provider response was too large")
                payload = json.loads(raw)
        except (OSError, urllib.error.HTTPError, json.JSONDecodeError) as exc:
            raise SearchProviderError("the search provider request failed") from exc

        results = payload.get("web", {}).get("results", [])
        return [
            SearchResult(
                url=str(item.get("url", "")),
                title=str(item.get("title", ""))[:300],
                snippet=str(item.get("description", ""))[:1000],
            )
            for item in results
            if isinstance(item, dict) and item.get("url") and item.get("title")
        ]
