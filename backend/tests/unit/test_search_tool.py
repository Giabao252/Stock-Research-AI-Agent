"""
Unit tests for mcp_servers/search_tool.py.
"""

from unittest.mock import AsyncMock, patch

from app.clients.tavily import NewsResult
from app.mcp_servers.search_tool import ToolError, web_search_tool


async def test_web_search_tool_wraps_results():
    news = [
        NewsResult(title="Apple beats earnings", url="https://news.example/1", snippet="...", published="2026-01-01"),
    ]
    with patch("app.mcp_servers.search_tool.search", new=AsyncMock(return_value=news)):
        result = await web_search_tool("AAPL earnings")

    assert result.query == "AAPL earnings"
    assert result.results == news


async def test_web_search_tool_empty_results():
    with patch("app.mcp_servers.search_tool.search", new=AsyncMock(return_value=[])):
        result = await web_search_tool("AAPL earnings")

    assert result.results == []


async def test_web_search_tool_returns_tool_error_on_exception():
    with patch("app.mcp_servers.search_tool.search", new=AsyncMock(side_effect=RuntimeError("tavily down"))):
        result = await web_search_tool("AAPL earnings")

    assert isinstance(result, ToolError)
    assert result.tool == "web_search_tool"
    assert "tavily down" in result.message
