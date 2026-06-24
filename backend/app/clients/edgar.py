"""
SEC EDGAR client: ticker → CIK lookup, filings list, raw document fetch.

Public API:
    get_cik(ticker)                                  -> str (zero-padded 10-digit CIK)
    get_filings(cik, form_type="10-K", limit=5)      -> list[FilingMeta]
    fetch_filing_doc(cik, accession_number, filename) -> bytes
"""
import time

import httpx
from pydantic import BaseModel
from tenacity import retry, retry_if_exception_type, stop_after_attempt, wait_exponential

from app.config import settings

TICKERS_URL = "https://www.sec.gov/files/company_tickers.json"
SUBMISSIONS_BASE = "https://data.sec.gov/submissions"
ARCHIVES_BASE = "https://www.sec.gov/Archives/edgar/data"

_CACHE_TTL = 86_400.0  # 24-hour TTL cache


class EDGARTickerNotFound(Exception):
    """Raised when a ticker symbol has no CIK entry in SEC EDGAR."""


class EDGARFetchError(Exception):
    """Raised when an EDGAR HTTP request fails after retries."""


# ---------------------------------------------------------------------------
# Data return format
# ---------------------------------------------------------------------------


class FilingMeta(BaseModel):
    accession_number: str  # dashed format: "0000320193-24-000001"
    form_type: str
    filed_date: str
    primary_document: str
    cik: str  # zero-padded 10 digits


# ---------------------------------------------------------------------------
# Module-level cache and HTTP client
# ---------------------------------------------------------------------------

_ticker_cache: dict[str, str] | None = None
_ticker_cache_ts: float = 0.0

_http_client = httpx.AsyncClient(
    headers={"User-Agent": f"{settings.sec_user_name} {settings.sec_user_email}"},
    timeout=httpx.Timeout(30.0),
    follow_redirects=True,
)


# ---------------------------------------------------------------------------
# Private retry-wrapped GET helper
# ---------------------------------------------------------------------------


@retry(
    retry=retry_if_exception_type(httpx.TransportError),
    stop=stop_after_attempt(3),
    wait=wait_exponential(multiplier=1, min=1, max=8),
    reraise=True,
)
async def _get(url: str) -> httpx.Response:
    response = await _http_client.get(url)
    response.raise_for_status()
    return response


def _normalize_accession(raw: str) -> str:
    """Ensure accession number is in dashed format: XXXXXXXXXX-YY-ZZZZZZ."""
    clean = raw.replace("-", "")
    if len(clean) != 18:
        return raw
    return f"{clean[:10]}-{clean[10:12]}-{clean[12:]}"


# ---------------------------------------------------------------------------
# Public API fetches
# ---------------------------------------------------------------------------


async def get_cik(ticker: str) -> str:
    """Return the zero-padded 10-digit CIK for a given ticker symbol.

    The company_tickers.json is fetched once and cached in memory for 24h.
    Raises EDGARTickerNotFound if the ticker has no EDGAR entry.
    Raises EDGARFetchError on network/HTTP failures.
    """
    global _ticker_cache, _ticker_cache_ts

    if _ticker_cache is None or time.time() - _ticker_cache_ts >= _CACHE_TTL:
        try:
            response = await _get(TICKERS_URL)
        except httpx.HTTPStatusError as exc:
            raise EDGARFetchError(
                f"Failed to fetch company tickers (HTTP {exc.response.status_code})"
            ) from exc
        except httpx.TransportError as exc:
            raise EDGARFetchError(f"Network error fetching company tickers: {exc}") from exc

        data: dict = response.json()
        _ticker_cache = {
            entry["ticker"].upper(): str(entry["cik_str"]).zfill(10)
            for entry in data.values()
        }
        _ticker_cache_ts = time.time()

    cik = _ticker_cache.get(ticker.upper())
    if cik is None:
        raise EDGARTickerNotFound(f"No EDGAR entry for ticker: {ticker!r}")
    return cik


async def get_filings(
    cik: str,
    form_type: str = "10-K",
    limit: int = 5,
) -> list[FilingMeta]:
    """Return the most recent `limit` filings of `form_type` for the given CIK.

    Raises EDGARFetchError on network/HTTP failures.
    """
    url = f"{SUBMISSIONS_BASE}/CIK{cik}.json"
    try:
        response = await _get(url)
    except httpx.HTTPStatusError as exc:
        raise EDGARFetchError(
            f"Failed to fetch submissions for CIK {cik} (HTTP {exc.response.status_code})"
        ) from exc
    except httpx.TransportError as exc:
        raise EDGARFetchError(f"Network error fetching submissions for CIK {cik}: {exc}") from exc

    recent = response.json()["filings"]["recent"]
    forms: list[str] = recent["form"]
    dates: list[str] = recent["filingDate"]
    accessions: list[str] = recent["accessionNumber"]
    primaries: list[str] = recent["primaryDocument"]

    results: list[FilingMeta] = []
    for form, date, accession, primary in zip(forms, dates, accessions, primaries):
        if form != form_type:
            continue
        results.append(
            FilingMeta(
                accession_number=_normalize_accession(accession),
                form_type=form,
                filed_date=date,
                primary_document=primary,
                cik=cik,
            )
        )
        if len(results) >= limit:
            break

    return results


async def fetch_filing_doc(cik: str, accession_number: str, filename: str) -> bytes:
    """Fetch raw bytes for a specific SEC filing document.

    SEC archive paths use the integer CIK (no leading zeros) and the
    accession number with dashes stripped.
    Raises EDGARFetchError on network/HTTP failures.
    """
    accession_no_dashes = accession_number.replace("-", "")
    cik_int = int(cik)  # strip leading zeros for archive URL
    url = f"{ARCHIVES_BASE}/{cik_int}/{accession_no_dashes}/{filename}"

    try:
        response = await _get(url)
    except httpx.HTTPStatusError as exc:
        raise EDGARFetchError(
            f"Failed to fetch filing doc {filename} for CIK {cik} "
            f"(HTTP {exc.response.status_code})"
        ) from exc
    except httpx.TransportError as exc:
        raise EDGARFetchError(
            f"Network error fetching filing doc {filename} for CIK {cik}: {exc}"
        ) from exc

    return response.content
