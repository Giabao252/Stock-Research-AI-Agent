"""
Unit tests for mcp_servers/stock_tool.py.
"""

from unittest.mock import AsyncMock, patch

from app.clients.alpha_vantage import AlphaVantageTickerNotFound, CompanyOverview, StockQuote
from app.mcp_servers.stock_tool import ToolError, stock_data_tool


def make_quote() -> StockQuote:
    return StockQuote(
        ticker="AAPL", price=200.0, previous_close=198.0, change=2.0,
        change_percent=1.0, volume=1000, latest_trading_day="2026-01-01",
    )


def make_overview() -> CompanyOverview:
    return CompanyOverview(
        ticker="AAPL", name="Apple", pe_ratio=30.0, market_cap=3e12, revenue_ttm=4e11,
        eps=6.5, beta=1.2, week_52_high=220.0, week_52_low=150.0, dividend_yield=0.005,
    )


async def test_stock_data_tool_maps_every_field():
    quote, overview = make_quote(), make_overview()
    with (
        patch("app.mcp_servers.stock_tool.get_quote", new=AsyncMock(return_value=quote)),
        patch("app.mcp_servers.stock_tool.get_overview", new=AsyncMock(return_value=overview)),
    ):
        result = await stock_data_tool("AAPL")

    assert result.ticker == "AAPL"
    assert result.price == quote.price
    assert result.previous_close == quote.previous_close
    assert result.change == quote.change
    assert result.change_percent == quote.change_percent
    assert result.volume == quote.volume
    assert result.latest_trading_day == quote.latest_trading_day
    assert result.pe_ratio == overview.pe_ratio
    assert result.market_cap == overview.market_cap
    assert result.revenue_ttm == overview.revenue_ttm
    assert result.eps == overview.eps
    assert result.beta == overview.beta
    assert result.week_52_high == overview.week_52_high
    assert result.week_52_low == overview.week_52_low


async def test_stock_data_tool_ticker_not_found():
    with (
        patch("app.mcp_servers.stock_tool.get_quote", new=AsyncMock(side_effect=AlphaVantageTickerNotFound("ZZZZ"))),
        patch("app.mcp_servers.stock_tool.get_overview", new=AsyncMock(return_value=make_overview())),
    ):
        result = await stock_data_tool("ZZZZ")

    assert isinstance(result, ToolError)
    assert result.tool == "stock-data-tool"
    assert "ZZZZ" in result.message


async def test_stock_data_tool_generic_exception():
    with (
        patch("app.mcp_servers.stock_tool.get_quote", new=AsyncMock(side_effect=RuntimeError("rate limited"))),
        patch("app.mcp_servers.stock_tool.get_overview", new=AsyncMock(return_value=make_overview())),
    ):
        result = await stock_data_tool("AAPL")

    assert isinstance(result, ToolError)
    assert result.tool == "stock-data-tool"
    assert "rate limited" in result.message
