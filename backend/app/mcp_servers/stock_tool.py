"""
MCP tool: stock_data_tool

Fetches live financial metrics - the numbers that go into ResearchReport.metrics
and the MetricsHeader component on the frontend

Agent calls it once per session
"""

import asyncio

from fastmcp import FastMCP
from pydantic import BaseModel

from app.clients.alpha_vantage import get_quote, get_overview, AlphaVantageTickerNotFound

mcp = FastMCP('stock-data')

class StockMetrics(BaseModel):
    ticker: str
    price: float
    previous_close: float
    change: float
    change_percent: float
    volume: int
    latest_trading_day: str
    pe_ratio: float | None
    market_cap: float | None
    revenue_ttm: float | None
    eps: float | None
    beta: float | None
    week_52_high: float | None
    week_52_low: float | None


class ToolError(BaseModel):
    tool: str
    message: str

@mcp.tool()
async def stock_data_tool(ticker: str) -> StockMetrics | ToolError:
    try:
        quote, company_overview = await asyncio.gather(
            get_quote(ticker),
            get_overview(ticker)
        )
    
    except AlphaVantageTickerNotFound as exc:
        return ToolError(
            tool="stock-data-tool", 
            message=f"Ticker '{ticker}' not found. Message: {exc}"
            )


    except Exception as exc:
        return ToolError(
            tool="stock-data-tool", 
            message=f"Error fetching stock data for ticker '{ticker}': {exc}"
            )
    return StockMetrics(
        ticker=ticker,
        price=quote.price,
        previous_close=quote.previous_close,
        change=quote.change,
        change_percent=quote.change_percent,
        volume=quote.volume,
        latest_trading_day=quote.latest_trading_day,
        pe_ratio=company_overview.pe_ratio,
        market_cap=company_overview.market_cap,
        revenue_ttm=company_overview.revenue_ttm,
        eps=company_overview.eps,
        beta=company_overview.beta,
        week_52_high=company_overview.week_52_high,
        week_52_low=company_overview.week_52_low
    )