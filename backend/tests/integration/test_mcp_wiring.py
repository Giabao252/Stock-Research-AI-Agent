"""
Tier 2 integration tests: exercise the real MCP protocol layer via
fastmcp.Client(mcp) — in-process, no live HTTP server needed (Client accepts a
FastMCP instance directly as its transport). This proves the composed server
in app/mcp_servers/server.py exposes the tool names agent/runner.py's
allowed_tools=["mcp__stock-research__*"] wildcard depends on, and that each
tool's real MCP registration (decorator, mount, Pydantic serialization) works
end to end — not just the business logic inside each tool function, which is
covered separately in tests/unit/test_*_tool.py.

External API clients (edgar, openai, qdrant, cohere, alpha_vantage, tavily)
are mocked at the same boundary the Tier 1 tool tests use — this tier is about
MCP wiring, not third-party data. code_execution_tool needs no mocking, it's
pure RestrictedPython.
"""

from unittest.mock import AsyncMock, patch

from fastmcp import Client

from app.clients.alpha_vantage import CompanyOverview, StockQuote
from app.clients.tavily import NewsResult
from app.mcp_servers.server import mcp
from app.models.chunk import Chunk

EXPECTED_TOOL_NAMES = {
    "rag_retrieval_tool",
    "edgar_fetch_tool",
    "stock_data_tool",
    "web_search_tool",
    "code_execution_tool",
}


async def test_list_tools_exposes_expected_names_unprefixed():
    async with Client(mcp) as client:
        tools = await client.list_tools()

    assert {t.name for t in tools} == EXPECTED_TOOL_NAMES


async def test_call_tool_rag_retrieval_routes_through_mcp_protocol():
    chunk = Chunk(
        chunk_id="aaa",
        text="Apple faces competition risk",
        ticker="AAPL",
        section="Item 1A",
        year=2024,
        source_url="https://sec.gov/test",
        score=0.9,
    )
    with patch("app.mcp_servers.rag_tool.retrieve", new=AsyncMock(return_value=[chunk])):
        async with Client(mcp) as client:
            result = await client.call_tool("rag_retrieval_tool", {"query": "risk", "ticker": "AAPL"})

    assert result.data.ticker == "AAPL"
    assert result.data.chunks[0].chunk_id == "aaa"


async def test_call_tool_edgar_fetch_routes_through_mcp_protocol():
    with patch("app.mcp_servers.edgar_tool.ingest_ticker", new=AsyncMock(return_value=12)):
        async with Client(mcp) as client:
            result = await client.call_tool("edgar_fetch_tool", {"ticker": "AAPL"})

    assert result.data.ticker == "AAPL"
    assert result.data.chunks_upserted == 12
    assert result.data.status == "success"


async def test_call_tool_edgar_fetch_zero_chunks_status():
    with patch("app.mcp_servers.edgar_tool.ingest_ticker", new=AsyncMock(return_value=0)):
        async with Client(mcp) as client:
            result = await client.call_tool("edgar_fetch_tool", {"ticker": "ZZZZ"})

    assert result.data.status == "no_filings_found"


async def test_call_tool_stock_data_routes_through_mcp_protocol():
    quote = StockQuote(
        ticker="AAPL", price=200.0, previous_close=198.0, change=2.0,
        change_percent=1.0, volume=1000, latest_trading_day="2026-01-01",
    )
    overview = CompanyOverview(
        ticker="AAPL", name="Apple", pe_ratio=30.0, market_cap=3e12, revenue_ttm=4e11,
        eps=6.5, beta=1.2, week_52_high=220.0, week_52_low=150.0, dividend_yield=0.005,
    )
    with (
        patch("app.mcp_servers.stock_tool.get_quote", new=AsyncMock(return_value=quote)),
        patch("app.mcp_servers.stock_tool.get_overview", new=AsyncMock(return_value=overview)),
    ):
        async with Client(mcp) as client:
            result = await client.call_tool("stock_data_tool", {"ticker": "AAPL"})

    assert result.data.ticker == "AAPL"
    assert result.data.pe_ratio == 30.0


async def test_call_tool_web_search_routes_through_mcp_protocol():
    news = NewsResult(title="Apple beats earnings", url="https://news.example/1", snippet="...", published="2026-01-01")
    with patch("app.mcp_servers.search_tool.search", new=AsyncMock(return_value=[news])):
        async with Client(mcp) as client:
            result = await client.call_tool("web_search_tool", {"query": "AAPL earnings"})

    assert result.data.query == "AAPL earnings"
    assert result.data.results[0].title == "Apple beats earnings"


async def test_call_tool_code_execution_real_no_mocking():
    async with Client(mcp) as client:
        result = await client.call_tool("code_execution_tool", {"code": "result = 1 + 1", "context": {}})

    assert result.data.result == 2
    assert result.data.error is None
