"""
MCP tool: stock_data_tool

Fetches live financial metrics - the numbers that go into ResearchReport.metrics
and the MetricsHeader component on the frontend

Agent calls it once per session. Results are cached in Redis (shared across the MCP
service's restarts and the runs of different sessions) to protect Alpha Vantage's
25 requests/day free-tier limit.
"""

from fastmcp import FastMCP
from pydantic import BaseModel

from app.clients import redis as redis_client
from app.clients.alpha_vantage import (
    AlphaVantagePremiumError,
    AlphaVantageTickerNotFound,
    get_overview,
    get_quote,
    get_ttm_eps,
)

mcp = FastMCP('stock-data')

STOCK_CACHE_TTL_SECONDS = 900  # 15 minutes

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
    cache_key = f"stock:{ticker.upper()}"
    cached = await redis_client.get_cached(cache_key)
    if cached:
        try:
            return StockMetrics.model_validate_json(cached)
        except ValueError:
            pass  # stale/incompatible entry — fall through and refetch

    company_overview = None
    ttm_eps = None
    try:
        # Sequential, not gathered: Alpha Vantage's free tier allows 1 request/second,
        # and a failed quote shouldn't burn a second request on the overview.
        quote = await get_quote(ticker)
        try:
            company_overview = await get_overview(ticker)
        except AlphaVantagePremiumError:
            # OVERVIEW is premium-only on the free plan; fall back to what EARNINGS can give us.
            ttm_eps = await get_ttm_eps(ticker)

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

    if company_overview is not None:
        fundamentals = company_overview.model_dump(
            include={"pe_ratio", "market_cap", "revenue_ttm", "eps", "beta", "week_52_high", "week_52_low"}
        )
    else:
        fundamentals = dict.fromkeys(
            ("pe_ratio", "market_cap", "revenue_ttm", "eps", "beta", "week_52_high", "week_52_low")
        )
        fundamentals["eps"] = ttm_eps
        if ttm_eps and ttm_eps > 0:
            fundamentals["pe_ratio"] = round(quote.price / ttm_eps, 2)

    metrics = StockMetrics(
        ticker=ticker,
        price=quote.price,
        previous_close=quote.previous_close,
        change=quote.change,
        change_percent=quote.change_percent,
        volume=quote.volume,
        latest_trading_day=quote.latest_trading_day,
        **fundamentals,
    )
    await redis_client.set_cached(cache_key, metrics.model_dump_json(), STOCK_CACHE_TTL_SECONDS)
    return metrics
