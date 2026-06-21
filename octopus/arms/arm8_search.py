"""Arm 8 — Web Search: lightweight search and URL fetch for enrichment."""

from __future__ import annotations

import httpx


class WebSearch:
    """Minimal web fetcher. For production, wire in a proper search API
    (Brave, Serper, Tavily) by setting the SEARCH_API_KEY env var."""

    def __init__(self, api_key: str | None = None) -> None:
        import os
        self._key = api_key or os.environ.get("SEARCH_API_KEY", "")

    def fetch_url(self, url: str, timeout: int = 10) -> str:
        """Fetch the text content of a URL."""
        resp = httpx.get(url, timeout=timeout, follow_redirects=True)
        resp.raise_for_status()
        # Strip HTML tags naively for LLM consumption
        import re
        text = re.sub(r"<[^>]+>", " ", resp.text)
        text = re.sub(r"\s{2,}", " ", text)
        return text[:8000]

    def search(self, query: str, num_results: int = 5) -> list[dict]:
        """Search via Brave Search API, falling back to DuckDuckGo if no key is set."""
        if self._key:
            return self._brave_search(query, num_results)
        return self._ddg_search(query, num_results)

    def _brave_search(self, query: str, num_results: int) -> list[dict]:
        headers = {
            "Accept": "application/json",
            "Accept-Encoding": "gzip",
            "X-Subscription-Token": self._key,
        }
        resp = httpx.get(
            "https://api.search.brave.com/res/v1/web/search",
            params={"q": query, "count": num_results},
            headers=headers,
            timeout=10,
        )
        resp.raise_for_status()
        data = resp.json()
        return [
            {"title": r.get("title"), "url": r.get("url"), "description": r.get("description")}
            for r in data.get("web", {}).get("results", [])
        ]

    def _ddg_search(self, query: str, num_results: int) -> list[dict]:
        """DuckDuckGo instant-answer API — no key required, best-effort results."""
        resp = httpx.get(
            "https://api.duckduckgo.com/",
            params={"q": query, "format": "json", "no_redirect": "1", "no_html": "1"},
            headers={"User-Agent": "Octopus/0.1"},
            timeout=10,
            follow_redirects=True,
        )
        resp.raise_for_status()
        data = resp.json()
        results = []
        if data.get("AbstractURL"):
            results.append({
                "title": data.get("Heading", query),
                "url": data["AbstractURL"],
                "description": data.get("AbstractText", ""),
            })
        for topic in data.get("RelatedTopics", [])[:num_results - len(results)]:
            if "FirstURL" in topic:
                results.append({
                    "title": topic.get("Text", "")[:80],
                    "url": topic["FirstURL"],
                    "description": topic.get("Text", ""),
                })
        return results or [{"title": "No results", "url": "", "description": f"DuckDuckGo returned no results for: {query}"}]
