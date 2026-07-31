"""
Unit tests for mcp_servers/edgar_tool.py.
"""

from unittest.mock import AsyncMock, patch

from app.mcp_servers.edgar_tool import ToolError, edgar_fetch_tool


async def test_edgar_fetch_tool_success_status():
    with patch("app.mcp_servers.edgar_tool.ingest_ticker", new=AsyncMock(return_value=12)):
        result = await edgar_fetch_tool("AAPL")

    assert result.ticker == "AAPL"
    assert result.chunks_upserted == 12
    assert result.status == "success"


async def test_edgar_fetch_tool_zero_chunks_status_is_exact_literal():
    with patch("app.mcp_servers.edgar_tool.ingest_ticker", new=AsyncMock(return_value=0)):
        result = await edgar_fetch_tool("ZZZZ")

    assert result.chunks_upserted == 0
    # docstring/comment says "no filings found" but the code literal is "no_filings_found"
    assert result.status == "no_filings_found"


async def test_edgar_fetch_tool_returns_tool_error_on_exception():
    with patch("app.mcp_servers.edgar_tool.ingest_ticker", new=AsyncMock(side_effect=RuntimeError("ticker not found"))):
        result = await edgar_fetch_tool("ZZZZ")

    assert isinstance(result, ToolError)
    assert result.tool == "edgar_fetch_tool"
    assert "ticker not found" in result.message
