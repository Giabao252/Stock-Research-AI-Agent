"""
current price and company fundamentals.

Public API:
    get_quote(ticker)    -> StockQuote
    get_overview(ticker) -> CompanyOverview

Free tier: 25 requests/day, 5 requests/minute.
OVERVIEW responses are cached in memory for 1 hour to stay within the daily limit.
"""

import time

import httpx
from pydantic import BaseModel

from app.config import settings

BASE_URL = "https://www.alphavantage.co/query"
OVERVIEW_CACHE_TTL = 3600.0  # 1 hour


class AlphaVantageError(Exception):
    """Raised when Alpha Vantage returns a rate-limit or auth error response."""


class AlphaVantageTickerNotFound(Exception):
    """Raised when Alpha Vantage returns no data for the given ticker."""


class StockQuote(BaseModel):
    ticker: str
    price: float
    previous_close: float
    change: float
    change_percent: float
    volume: int
    latest_trading_day: str


class CompanyOverview(BaseModel):
    ticker: str
    name: str
    pe_ratio: float | None
    market_cap: float | None
    revenue_ttm: float | None
    eps: float | None
    beta: float | None
    week_52_high: float | None
    week_52_low: float | None
    dividend_yield: float | None


# HTTP client and in-memory OVERVIEW cache

_http_client = httpx.AsyncClient(timeout=httpx.Timeout(30.0))

# {ticker_upper: (CompanyOverview, timestamp)}
_overview_cache: dict[str, tuple[CompanyOverview, float]] = {}


# Private helpers


async def _get(function: str, symbol: str) -> dict:
    response = await _http_client.get(
        BASE_URL,
        params={
            "function": function,
            "symbol": symbol,
            "apikey": settings.alpha_vantage_key,
        },
    )
    response.raise_for_status()
    data: dict = response.json()

    # Alpha Vantage signals rate-limiting or auth failure via these keys instead of HTTP 4xx
    if "Note" in data or "Information" in data:
        msg = data.get("Note") or data.get("Information", "Unknown Alpha Vantage error")
        raise AlphaVantageError(f"Alpha Vantage error: {msg}")

    return data


def _parse_float(value: str | None) -> float | None:
    """Convert an Alpha Vantage string field to float; None for 'None', '-', or missing."""
    if not value or value in ("None", "-", "N/A"):
        return None
    try:
        return float(value)
    except ValueError:
        return None


# Public API functions



async def get_quote(ticker: str) -> StockQuote:
    """Return current price data for `ticker`.

    Raises AlphaVantageTickerNotFound if the ticker is unknown to Alpha Vantage.
    Raises AlphaVantageError on rate-limit or auth failure.
    """
    data = await _get("GLOBAL_QUOTE", ticker)
    quote = data.get("Global Quote", {})

    if not quote or not quote.get("05. price"):
        raise AlphaVantageTickerNotFound(f"No quote data for ticker: {ticker!r}")

    change_pct_raw = quote.get("10. change percent", "0%").replace("%", "")

    return StockQuote(
        ticker=ticker.upper(),
        price=float(quote["05. price"]),
        previous_close=float(quote.get("08. previous close", 0)),
        change=float(quote.get("09. change", 0)),
        change_percent=float(change_pct_raw or 0),
        volume=int(quote.get("06. volume", 0)),
        latest_trading_day=quote.get("07. latest trading day", ""),
    )


async def get_overview(ticker: str) -> CompanyOverview:
    """Return company fundamentals for `ticker`.

    Results are cached in memory for 1 hour so repeated agent calls within a session
    don't burn the 25 req/day free-tier limit.
    Raises AlphaVantageTickerNotFound if the ticker is unknown to Alpha Vantage.
    Raises AlphaVantageError on rate-limit or auth failure.
    """
    upper = ticker.upper()

    cached = _overview_cache.get(upper)
    if cached and time.time() - cached[1] < OVERVIEW_CACHE_TTL:
        return cached[0]

    data = await _get("OVERVIEW", upper)

    if not data or "Symbol" not in data:
        raise AlphaVantageTickerNotFound(f"No overview data for ticker: {ticker!r}")

    overview = CompanyOverview(
        ticker=upper,
        name=data.get("Name", ""),
        pe_ratio=_parse_float(data.get("PERatio")),
        market_cap=_parse_float(data.get("MarketCapitalization")),
        revenue_ttm=_parse_float(data.get("RevenueTTM")),
        eps=_parse_float(data.get("EPS")),
        beta=_parse_float(data.get("Beta")),
        week_52_high=_parse_float(data.get("52WeekHigh")),
        week_52_low=_parse_float(data.get("52WeekLow")),
        dividend_yield=_parse_float(data.get("DividendYield")),
    )

    _overview_cache[upper] = (overview, time.time())
    return overview
