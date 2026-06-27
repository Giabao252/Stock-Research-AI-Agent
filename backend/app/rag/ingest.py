"""
Ingestion pipeline orchestrator: raw ticker data to Qdrant.

Public API:
    ingest_ticker(ticker, limit=5) -> int   (total chunks upserted)

Assumes Qdrant collections already exist (init_collections() called at app startup).
Exceptions from edgar, embedder, and qdrant propagate to the caller (MCP tool layer).
"""

import asyncio

from app.clients import edgar, qdrant as qdrant_client
from app.rag import chunker, embedder


async def ingest_ticker(ticker: str, limit: int = 5) -> int:
    """Fetch, chunk, embed, and upsert the most recent `limit` 10-K filings for a ticker.

    Returns the total number of chunks upserted across all filings.
    Filings are processed sequentially to stay within OpenAI embedding rate limits.
    """
    cik = await edgar.get_cik(ticker)
    filings = await edgar.get_filings(cik, form_type="10-K", limit=limit)

    total_chunks = 0

    for filing in filings:
        accession_no_dashes = filing.accession_number.replace("-", "")
        source_url = (
            f"{edgar.ARCHIVES_BASE}/{int(filing.cik)}"
            f"/{accession_no_dashes}/{filing.primary_document}"
        )
        year = int(filing.filed_date[:4])

        raw_bytes = await edgar.fetch_filing_doc(
            cik, filing.accession_number, filing.primary_document
        )
        chunks = await asyncio.to_thread(
            chunker.chunk_filing, raw_bytes, ticker, year, source_url
        )
        pairs = await embedder.embed_chunks(chunks)
        await qdrant_client.upsert_chunks(pairs)

        total_chunks += len(chunks)

    return total_chunks
