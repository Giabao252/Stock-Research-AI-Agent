"""
Unit tests for clients/alpha_vantage.py.
"""

import time
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.clients import alpha_vantage
from app.clients.alpha_vantage import (
    AlphaVantageError,
    AlphaVantageTickerNotFound,
    CompanyOverview,
    _parse_float,
    get_overview,
    get_quote,
)


@pytest.fixture(autouse=True)
def reset_overview_cache():
    alpha_vantage._overview_cache.clear()
    yield
    alpha_vantage._overview_cache.clear()


# ---------------------------------------------------------------------------
# _parse_float
# ---------------------------------------------------------------------------

@pytest.mark.parametrize("raw,expected", [
    (None, None),
    ("None", None),
    ("-", None),
    ("N/A", None),
    ("", None),
    ("not-a-number", None),
    ("35.2", 35.2),
    ("0", 0.0),
])
def test_parse_float(raw, expected):
    assert _parse_float(raw) == expected


# ---------------------------------------------------------------------------
# get_quote
# ---------------------------------------------------------------------------

async def test_get_quote_happy_path():
    data = {
        "Global Quote": {
            "05. price": "200.50",
            "08. previous close": "198.00",
            "09. change": "2.50",
            "10. change percent": "1.26%",
            "06. volume": "1000000",
            "07. latest trading day": "2026-01-01",
        }
    }
    with patch("app.clients.alpha_vantage._get", new=AsyncMock(return_value=data)):
        quote = await get_quote("aapl")

    assert quote.ticker == "AAPL"
    assert quote.price == 200.50
    assert quote.previous_close == 198.00
    assert quote.change == 2.50
    assert quote.change_percent == 1.26
    assert quote.volume == 1000000
    assert quote.latest_trading_day == "2026-01-01"


async def test_get_quote_ticker_not_found():
    with patch("app.clients.alpha_vantage._get", new=AsyncMock(return_value={"Global Quote": {}})):
        with pytest.raises(AlphaVantageTickerNotFound):
            await get_quote("ZZZZ")


# ---------------------------------------------------------------------------
# get_overview — cache behavior
# ---------------------------------------------------------------------------

def make_overview_data():
    return {
        "Symbol": "AAPL", "Name": "Apple Inc.", "PERatio": "30.5", "MarketCapitalization": "3000000000000",
        "RevenueTTM": "400000000000", "EPS": "6.5", "Beta": "1.2", "52WeekHigh": "220.0",
        "52WeekLow": "150.0", "DividendYield": "0.005",
    }


async def test_get_overview_happy_path_and_populates_cache():
    with patch("app.clients.alpha_vantage._get", new=AsyncMock(return_value=make_overview_data())) as mock_get:
        overview = await get_overview("aapl")

    assert overview.ticker == "AAPL"
    assert overview.name == "Apple Inc."
    assert overview.pe_ratio == 30.5
    assert mock_get.await_count == 1
    assert "AAPL" in alpha_vantage._overview_cache


async def test_get_overview_cache_hit_makes_no_http_call():
    cached_overview = CompanyOverview(
        ticker="AAPL", name="Apple Inc.", pe_ratio=30.5, market_cap=3e12, revenue_ttm=4e11,
        eps=6.5, beta=1.2, week_52_high=220.0, week_52_low=150.0, dividend_yield=0.005,
    )
    alpha_vantage._overview_cache["AAPL"] = (cached_overview, time.time())

    with patch("app.clients.alpha_vantage._get", new=AsyncMock()) as mock_get:
        overview = await get_overview("AAPL")

    assert overview is cached_overview
    mock_get.assert_not_awaited()


async def test_get_overview_expired_cache_refetches():
    stale_overview = CompanyOverview(
        ticker="AAPL", name="Stale", pe_ratio=1.0, market_cap=1.0, revenue_ttm=1.0,
        eps=1.0, beta=1.0, week_52_high=1.0, week_52_low=1.0, dividend_yield=1.0,
    )
    alpha_vantage._overview_cache["AAPL"] = (stale_overview, time.time() - alpha_vantage.OVERVIEW_CACHE_TTL - 1)

    with patch("app.clients.alpha_vantage._get", new=AsyncMock(return_value=make_overview_data())) as mock_get:
        overview = await get_overview("AAPL")

    assert mock_get.await_count == 1
    assert overview.name == "Apple Inc."


async def test_get_overview_ticker_not_found():
    with patch("app.clients.alpha_vantage._get", new=AsyncMock(return_value={})):
        with pytest.raises(AlphaVantageTickerNotFound):
            await get_overview("ZZZZ")


# ---------------------------------------------------------------------------
# _get — rate-limit/auth signaled via response body on HTTP 200
# ---------------------------------------------------------------------------

async def test_get_raises_alpha_vantage_error_on_note_key():
    resp = MagicMock()
    resp.raise_for_status = MagicMock()
    resp.json.return_value = {"Note": "Thank you for using Alpha Vantage! Our standard API rate limit is..."}

    with patch("app.clients.alpha_vantage._http_client.get", new=AsyncMock(return_value=resp)):
        with pytest.raises(AlphaVantageError):
            await get_quote("AAPL")


async def test_get_raises_alpha_vantage_error_on_information_key():
    resp = MagicMock()
    resp.raise_for_status = MagicMock()
    resp.json.return_value = {"Information": "Invalid API call"}

    with patch("app.clients.alpha_vantage._http_client.get", new=AsyncMock(return_value=resp)):
        with pytest.raises(AlphaVantageError):
            await get_overview("AAPL")


async def test_concurrent_requests_are_spaced_by_min_interval(monkeypatch):
    # Regression: stock_data_tool used to gather get_quote + get_overview, firing two
    # requests in the same instant and tripping Alpha Vantage's 1 request/second limit.
    import asyncio

    monkeypatch.setattr(alpha_vantage, "MIN_REQUEST_INTERVAL", 0.2)
    monkeypatch.setattr(alpha_vantage, "_last_request_at", 0.0)
    call_times: list[float] = []

    async def fake_get(*args, **kwargs):
        call_times.append(time.monotonic())
        response = MagicMock()
        response.json.return_value = {"ok": 1}
        return response

    with patch("app.clients.alpha_vantage._http_client.get", new=fake_get):
        await asyncio.gather(
            alpha_vantage._get("GLOBAL_QUOTE", "AAPL"),
            alpha_vantage._get("OVERVIEW", "AAPL"),
        )

    assert len(call_times) == 2
    assert call_times[1] - call_times[0] >= 0.19


async def test_get_redacts_api_key_echoed_in_error_message(monkeypatch):
    monkeypatch.setattr(alpha_vantage.settings, "alpha_vantage_key", "SECRETKEY123")
    resp = MagicMock()
    resp.raise_for_status = MagicMock()
    resp.json.return_value = {"Information": "We have detected your API key as SECRETKEY123 and the limit is 25/day."}

    with patch("app.clients.alpha_vantage._http_client.get", new=AsyncMock(return_value=resp)):
        with pytest.raises(AlphaVantageError) as exc_info:
            await get_quote("AAPL")

    assert "SECRETKEY123" not in str(exc_info.value)
    assert "[redacted]" in str(exc_info.value)


async def test_get_raises_premium_error_for_premium_endpoint_message():
    body = {"Information": "Thank you! This is a premium endpoint. You may subscribe..."}
    response = AsyncMock()
    response.json = lambda: body
    response.raise_for_status = lambda: None
    with patch("app.clients.alpha_vantage._http_client.get", new=AsyncMock(return_value=response)):
        with pytest.raises(alpha_vantage.AlphaVantagePremiumError):
            await alpha_vantage._get("OVERVIEW", "AAPL")


async def test_get_ttm_eps_sums_last_four_quarters():
    data = {"quarterlyEarnings": [{"reportedEPS": "2.0"}, {"reportedEPS": "1.5"}, {"reportedEPS": "1.0"}, {"reportedEPS": "0.5"}, {"reportedEPS": "9"}]}
    with patch("app.clients.alpha_vantage._get", new=AsyncMock(return_value=data)):
        assert await alpha_vantage.get_ttm_eps("AAPL") == 5.0


async def test_get_ttm_eps_none_when_data_incomplete():
    data = {"quarterlyEarnings": [{"reportedEPS": "2.0"}, {"reportedEPS": "None"}, {"reportedEPS": "1.0"}, {"reportedEPS": "0.5"}]}
    with patch("app.clients.alpha_vantage._get", new=AsyncMock(return_value=data)):
        assert await alpha_vantage.get_ttm_eps("AAPL") is None
