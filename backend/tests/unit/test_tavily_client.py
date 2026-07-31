"""
Unit tests for clients/tavily.py.
"""

from unittest.mock import AsyncMock, MagicMock, patch

import httpx
import pytest

from app.clients.tavily import TavilyError, search


def make_response(data: dict):
    resp = MagicMock()
    resp.json.return_value = data
    resp.raise_for_status = MagicMock()
    return resp


async def test_search_maps_fields():
    data = {
        "results": [
            {"title": "Apple beats earnings", "url": "https://news.example/1", "content": "summary", "published_date": "2026-01-01"},
        ]
    }
    with patch("app.clients.tavily._http_client.post", new=AsyncMock(return_value=make_response(data))):
        results = await search("AAPL earnings")

    assert len(results) == 1
    assert results[0].title == "Apple beats earnings"
    assert results[0].url == "https://news.example/1"
    assert results[0].snippet == "summary"
    assert results[0].published == "2026-01-01"


async def test_search_missing_fields_default_gracefully():
    data = {"results": [{}]}
    with patch("app.clients.tavily._http_client.post", new=AsyncMock(return_value=make_response(data))):
        results = await search("AAPL earnings")

    assert results[0].title == ""
    assert results[0].url == ""
    assert results[0].snippet == ""
    assert results[0].published is None


async def test_search_zero_results_returns_empty_list():
    with patch("app.clients.tavily._http_client.post", new=AsyncMock(return_value=make_response({"results": []}))):
        results = await search("obscure query")

    assert results == []


async def test_search_no_results_key_at_all_returns_empty_list():
    with patch("app.clients.tavily._http_client.post", new=AsyncMock(return_value=make_response({}))):
        results = await search("obscure query")

    assert results == []


async def test_search_http_error_raises_tavily_error():
    request = httpx.Request("POST", "https://api.tavily.com/search")
    response = httpx.Response(401, request=request, text="unauthorized")
    error = httpx.HTTPStatusError("error", request=request, response=response)

    mock_response = MagicMock()
    mock_response.raise_for_status.side_effect = error

    with patch("app.clients.tavily._http_client.post", new=AsyncMock(return_value=mock_response)):
        with pytest.raises(TavilyError):
            await search("AAPL earnings")
