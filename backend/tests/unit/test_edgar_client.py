"""
Unit tests for clients/edgar.py. _get is patched directly (bypassing tenacity
retry, which isn't the thing under test) except where the retry-wrapped HTTP
error handling itself is what's being verified.
"""

import time
from unittest.mock import AsyncMock, MagicMock, patch

import httpx
import pytest

from app.clients import edgar
from app.clients.edgar import (
    EDGARFetchError,
    EDGARTickerNotFound,
    _normalize_accession,
    fetch_filing_doc,
    get_cik,
    get_filings,
)


@pytest.fixture(autouse=True)
def reset_ticker_cache():
    edgar._ticker_cache = None
    edgar._ticker_cache_ts = 0.0
    yield
    edgar._ticker_cache = None
    edgar._ticker_cache_ts = 0.0


def make_tickers_response():
    resp = MagicMock()
    resp.json.return_value = {
        "0": {"ticker": "AAPL", "cik_str": 320193},
        "1": {"ticker": "MSFT", "cik_str": 789019},
    }
    return resp


def make_http_status_error(url: str, status_code: int) -> httpx.HTTPStatusError:
    request = httpx.Request("GET", url)
    response = httpx.Response(status_code, request=request)
    return httpx.HTTPStatusError("error", request=request, response=response)


# ---------------------------------------------------------------------------
# _normalize_accession
# ---------------------------------------------------------------------------

def test_normalize_accession_adds_dashes():
    assert _normalize_accession("000032019324000001") == "0000320193-24-000001"


def test_normalize_accession_round_trips_already_dashed():
    assert _normalize_accession("0000320193-24-000001") == "0000320193-24-000001"


def test_normalize_accession_passthrough_wrong_length():
    assert _normalize_accession("short") == "short"


# ---------------------------------------------------------------------------
# get_cik — cache behavior + error paths
# ---------------------------------------------------------------------------

async def test_get_cik_cache_miss_populates_cache():
    with patch("app.clients.edgar._get", new=AsyncMock(return_value=make_tickers_response())) as mock_get:
        cik = await get_cik("aapl")

    assert cik == "0000320193"
    assert mock_get.await_count == 1
    assert edgar._ticker_cache is not None


async def test_get_cik_cache_hit_makes_no_http_call():
    edgar._ticker_cache = {"AAPL": "0000320193"}
    edgar._ticker_cache_ts = time.time()

    with patch("app.clients.edgar._get", new=AsyncMock()) as mock_get:
        cik = await get_cik("AAPL")

    assert cik == "0000320193"
    mock_get.assert_not_awaited()


async def test_get_cik_expired_cache_refetches():
    edgar._ticker_cache = {"AAPL": "stale-value"}
    edgar._ticker_cache_ts = time.time() - edgar._CACHE_TTL - 1

    with patch("app.clients.edgar._get", new=AsyncMock(return_value=make_tickers_response())) as mock_get:
        cik = await get_cik("AAPL")

    assert mock_get.await_count == 1
    assert cik == "0000320193"


async def test_get_cik_unknown_ticker_raises():
    with patch("app.clients.edgar._get", new=AsyncMock(return_value=make_tickers_response())):
        with pytest.raises(EDGARTickerNotFound):
            await get_cik("ZZZZ")


async def test_get_cik_http_error_raises_fetch_error():
    error = make_http_status_error(edgar.TICKERS_URL, 500)
    with patch("app.clients.edgar._get", new=AsyncMock(side_effect=error)):
        with pytest.raises(EDGARFetchError):
            await get_cik("AAPL")


async def test_get_cik_transport_error_raises_fetch_error():
    with patch("app.clients.edgar._get", new=AsyncMock(side_effect=httpx.TransportError("no network"))):
        with pytest.raises(EDGARFetchError):
            await get_cik("AAPL")


# ---------------------------------------------------------------------------
# get_filings
# ---------------------------------------------------------------------------

def make_submissions_response(recent: dict):
    resp = MagicMock()
    resp.json.return_value = {"filings": {"recent": recent}}
    return resp


async def test_get_filings_filters_by_form_type_and_respects_limit():
    recent = {
        "form": ["10-K", "10-Q", "10-K", "10-K"],
        "filingDate": ["2024-01-01", "2024-02-01", "2023-01-01", "2022-01-01"],
        "accessionNumber": [
            "000032019324000001", "000032019324000002", "000032019323000001", "000032019322000001",
        ],
        "primaryDocument": [
            "aapl-20240101.htm", "aapl-20240201.htm", "aapl-20230101.htm", "aapl-20220101.htm",
        ],
    }
    with patch("app.clients.edgar._get", new=AsyncMock(return_value=make_submissions_response(recent))):
        results = await get_filings("0000320193", form_type="10-K", limit=2)

    assert len(results) == 2
    assert all(f.form_type == "10-K" for f in results)
    assert results[0].filed_date == "2024-01-01"
    assert results[0].accession_number == "0000320193-24-000001"


async def test_get_filings_http_error_raises_fetch_error():
    error = make_http_status_error(f"{edgar.SUBMISSIONS_BASE}/CIK0000320193.json", 404)
    with patch("app.clients.edgar._get", new=AsyncMock(side_effect=error)):
        with pytest.raises(EDGARFetchError):
            await get_filings("0000320193")


# ---------------------------------------------------------------------------
# fetch_filing_doc
# ---------------------------------------------------------------------------

async def test_fetch_filing_doc_returns_raw_bytes():
    resp = MagicMock()
    resp.content = b"<html>10-K content</html>"
    with patch("app.clients.edgar._get", new=AsyncMock(return_value=resp)):
        content = await fetch_filing_doc("0000320193", "0000320193-24-000001", "aapl-20240101.htm")

    assert content == b"<html>10-K content</html>"


async def test_fetch_filing_doc_http_error_raises_fetch_error():
    error = make_http_status_error(edgar.ARCHIVES_BASE, 403)
    with patch("app.clients.edgar._get", new=AsyncMock(side_effect=error)):
        with pytest.raises(EDGARFetchError):
            await fetch_filing_doc("0000320193", "0000320193-24-000001", "aapl.htm")
