"""
Data source for MCP web_search_tool which will be called by the agent when needing information that isnt
the 10-K filing

Public API:
    search(query, count=5) -> list[NewsResult]
"""

import httpx
from pydantic import BaseModel

from app.config import settings

SEARCH_URL = "https://api.tavily.com/search"


class TavilyError(Exception):
    """Raised when the Tavily API returns an error response."""


class NewsResult(BaseModel):
    title: str
    url: str
    snippet: str
    published: str | None


_http_client = httpx.AsyncClient(timeout=httpx.Timeout(30.0))


async def search(query: str, count: int = 5) -> list[NewsResult]:
    """Return up to `count` news results for `query`.

    Raises TavilyError on API errors.
    Returns an empty list if Tavily finds no results.
    """
    try:
        response = await _http_client.post(
            SEARCH_URL,
            json={
                "api_key": settings.tavily_api_key,
                "query": query,
                "max_results": count,
                "search_depth": "basic",
                "include_answer": False,
            },
        )
        response.raise_for_status()
    except httpx.HTTPStatusError as exc:
        raise TavilyError(
            f"Tavily API error (HTTP {exc.response.status_code}): {exc.response.text}"
        ) from exc

    data = response.json()

    return [
        NewsResult(
            title=r.get("title", ""),
            url=r.get("url", ""),
            snippet=r.get("content", ""),
            published=r.get("published_date"),
        )
        for r in data.get("results", [])
    ]
