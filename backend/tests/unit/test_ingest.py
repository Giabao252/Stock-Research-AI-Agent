"""
Unit tests for rag/ingest.py — the orchestrator. edgar/qdrant/chunker/embedder
are imported as modules into ingest.py, so patch targets are the module
attributes on app.rag.ingest, not the original definition modules.
"""

from unittest.mock import AsyncMock, patch

from app.clients.edgar import FilingMeta
from app.models.chunk import Chunk
from app.rag.ingest import ingest_ticker


def make_filing(accession="0000320193-24-000001", filed_date="2024-01-01", primary="aapl-20240101.htm", cik="0000320193"):
    return FilingMeta(accession_number=accession, form_type="10-K", filed_date=filed_date, primary_document=primary, cik=cik)


def make_chunk(chunk_id: str) -> Chunk:
    return Chunk(
        chunk_id=chunk_id, text="text", ticker="AAPL", section="Item 1A",
        year=2024, source_url="https://sec.gov/test", score=0.0,
    )


async def test_ingest_ticker_zero_filings_returns_zero_without_downstream_calls():
    with (
        patch("app.rag.ingest.edgar.get_cik", new=AsyncMock(return_value="0000320193")),
        patch("app.rag.ingest.edgar.get_filings", new=AsyncMock(return_value=[])),
        patch("app.rag.ingest.chunker.chunk_filing") as mock_chunk,
        patch("app.rag.ingest.embedder.embed_chunks", new=AsyncMock()) as mock_embed,
        patch("app.rag.ingest.qdrant_client.upsert_chunks", new=AsyncMock()) as mock_upsert,
    ):
        total = await ingest_ticker("AAPL")

    assert total == 0
    mock_chunk.assert_not_called()
    mock_embed.assert_not_awaited()
    mock_upsert.assert_not_awaited()


async def test_ingest_ticker_sequential_accumulation_across_filings():
    filings = [
        make_filing(accession="0000320193-24-000001", filed_date="2024-01-01"),
        make_filing(accession="0000320193-23-000001", filed_date="2023-01-01"),
    ]
    chunks_per_filing = [[make_chunk("a"), make_chunk("b")], [make_chunk("c")]]

    with (
        patch("app.rag.ingest.edgar.get_cik", new=AsyncMock(return_value="0000320193")),
        patch("app.rag.ingest.edgar.get_filings", new=AsyncMock(return_value=filings)),
        patch("app.rag.ingest.edgar.fetch_filing_doc", new=AsyncMock(return_value=b"raw bytes")),
        patch("app.rag.ingest.chunker.chunk_filing", side_effect=chunks_per_filing) as mock_chunk,
        patch(
            "app.rag.ingest.embedder.embed_chunks",
            new=AsyncMock(side_effect=lambda chunks: [(c, [0.0]) for c in chunks]),
        ) as mock_embed,
        patch("app.rag.ingest.qdrant_client.upsert_chunks", new=AsyncMock()) as mock_upsert,
    ):
        total = await ingest_ticker("AAPL", limit=2)

    assert total == 3
    assert mock_chunk.call_count == 2
    assert mock_embed.await_count == 2
    assert mock_upsert.await_count == 2


async def test_ingest_ticker_passes_fetched_bytes_and_derived_year_to_chunker():
    filings = [make_filing(filed_date="2024-06-15")]

    with (
        patch("app.rag.ingest.edgar.get_cik", new=AsyncMock(return_value="0000320193")),
        patch("app.rag.ingest.edgar.get_filings", new=AsyncMock(return_value=filings)),
        patch("app.rag.ingest.edgar.fetch_filing_doc", new=AsyncMock(return_value=b"specific raw bytes")),
        patch("app.rag.ingest.chunker.chunk_filing", return_value=[make_chunk("a")]) as mock_chunk,
        patch("app.rag.ingest.embedder.embed_chunks", new=AsyncMock(return_value=[(make_chunk("a"), [0.0])])),
        patch("app.rag.ingest.qdrant_client.upsert_chunks", new=AsyncMock()),
    ):
        await ingest_ticker("AAPL")

    args = mock_chunk.call_args[0]
    assert args[0] == b"specific raw bytes"
    assert args[1] == "AAPL"
    assert args[2] == 2024
