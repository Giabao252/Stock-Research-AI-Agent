"""
MCP tool: stock_data_tool

Fetches live financial metrics - the numbers that go into ResearchReport.metrics
and the MetricsHeader component on the frontend

Agent calls it once per session. Results are cached in Redis (shared across the MCP
service's restarts and the runs of different sessions) to protect Alpha Vantage's
25 requests/day free-tier limit. Fundamentals (EPS, market cap...) move quarterly, so they
are cached much longer than the quote: a repeat run costs one Alpha Vantage call, not two or three.
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
FUNDAMENTALS_CACHE_TTL_SECONDS = 86_400  # 24 hours

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


class Fundamentals(BaseModel):
    """The slow-moving half of StockMetrics, cached on its own for 24h."""

    pe_ratio: float | None = None
    market_cap: float | None = None
    revenue_ttm: float | None = None
    eps: float | None = None
    beta: float | None = None
    week_52_high: float | None = None
    week_52_low: float | None = None
    # True when only EPS was available: P/E is then derived from the live price on every read.
    derive_pe: bool = False


async def _load_fundamentals(ticker: str) -> Fundamentals | None:
    cached = await redis_client.get_cached(f"fundamentals:{ticker.upper()}")
    if not cached:
        return None
    try:
        return Fundamentals.model_validate_json(cached)
    except ValueError:
        return None  # stale/incompatible entry


async def _fetch_fundamentals(ticker: str) -> Fundamentals:
    try:
        overview = await get_overview(ticker)
    except AlphaVantagePremiumError:
        # OVERVIEW is premium-only on the free plan; fall back to what EARNINGS can give us.
        return Fundamentals(eps=await get_ttm_eps(ticker), derive_pe=True)
    return Fundamentals(**overview.model_dump(include=set(Fundamentals.model_fields) - {"derive_pe"}))


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

    try:
        # Sequential, not gathered: Alpha Vantage's free tier allows 1 request/second,
        # and a failed quote shouldn't burn a request on the fundamentals.
        quote = await get_quote(ticker)
        fundamentals = await _load_fundamentals(ticker)
        if fundamentals is None:
            fundamentals = await _fetch_fundamentals(ticker)
            await redis_client.set_cached(
                f"fundamentals:{ticker.upper()}", fundamentals.model_dump_json(), FUNDAMENTALS_CACHE_TTL_SECONDS
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

    values = fundamentals.model_dump(exclude={"derive_pe"})
    if fundamentals.derive_pe and fundamentals.eps and fundamentals.eps > 0:
        values["pe_ratio"] = round(quote.price / fundamentals.eps, 2)

    metrics = StockMetrics(
        ticker=ticker,
        price=quote.price,
        previous_close=quote.previous_close,
        change=quote.change,
        change_percent=quote.change_percent,
        volume=quote.volume,
        latest_trading_day=quote.latest_trading_day,
        **values,
    )
    await redis_client.set_cached(cache_key, metrics.model_dump_json(), STOCK_CACHE_TTL_SECONDS)
    return metrics
