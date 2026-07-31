"""
Unit tests for clients/qdrant.py — the one client that had no direct coverage
(test_retrieval.py only mocks query_dense away in its caller, it never
exercises these functions' own logic against the real AsyncQdrantClient
methods). _client's methods are always mocked here — no real network/cloud
call, consistent with the rest of this suite.
"""

from types import SimpleNamespace
from unittest.mock import AsyncMock, patch

from app.clients.qdrant import (
    FILINGS_COLLECTION,
    REPORTS_COLLECTION,
    VECTOR_SIZE,
    init_collections,
    query_dense,
    upsert_chunks,
)
from app.models.chunk import Chunk


def make_chunk(chunk_id="00000000000000ff", score=0.0) -> Chunk:
    return Chunk(
        chunk_id=chunk_id, text="Apple faces competition risk", ticker="AAPL",
        section="Item 1A", year=2024, source_url="https://sec.gov/test", score=score,
    )


def make_collections_response(names: list[str]):
    return SimpleNamespace(collections=[SimpleNamespace(name=n) for n in names])


# ---------------------------------------------------------------------------
# init_collections
# ---------------------------------------------------------------------------

async def test_init_collections_creates_both_when_neither_exists():
    with (
        patch("app.clients.qdrant._client.get_collections", new=AsyncMock(return_value=make_collections_response([]))),
        patch("app.clients.qdrant._client.create_collection", new=AsyncMock()) as mock_create,
        patch("app.clients.qdrant._client.create_payload_index", new=AsyncMock()),
    ):
        await init_collections()

    created_names = {call.kwargs["collection_name"] for call in mock_create.call_args_list}
    assert created_names == {FILINGS_COLLECTION, REPORTS_COLLECTION}
    for call in mock_create.call_args_list:
        assert call.kwargs["vectors_config"].size == VECTOR_SIZE


async def test_init_collections_skips_existing_ones():
    with (
        patch(
            "app.clients.qdrant._client.get_collections",
            new=AsyncMock(return_value=make_collections_response([FILINGS_COLLECTION])),
        ),
        patch("app.clients.qdrant._client.create_collection", new=AsyncMock()) as mock_create,
        patch("app.clients.qdrant._client.create_payload_index", new=AsyncMock()),
    ):
        await init_collections()

    created_names = {call.kwargs["collection_name"] for call in mock_create.call_args_list}
    assert created_names == {REPORTS_COLLECTION}


async def test_init_collections_creates_nothing_when_both_exist():
    with (
        patch(
            "app.clients.qdrant._client.get_collections",
            new=AsyncMock(return_value=make_collections_response([FILINGS_COLLECTION, REPORTS_COLLECTION])),
        ),
        patch("app.clients.qdrant._client.create_collection", new=AsyncMock()) as mock_create,
        patch("app.clients.qdrant._client.create_payload_index", new=AsyncMock()),
    ):
        await init_collections()

    mock_create.assert_not_awaited()


async def test_init_collections_always_ensures_payload_indexes():
    # Idempotent/self-healing: runs even when both collections already exist,
    # so a collection created before these indexes existed gets backfilled.
    with (
        patch(
            "app.clients.qdrant._client.get_collections",
            new=AsyncMock(return_value=make_collections_response([FILINGS_COLLECTION, REPORTS_COLLECTION])),
        ),
        patch("app.clients.qdrant._client.create_collection", new=AsyncMock()),
        patch("app.clients.qdrant._client.create_payload_index", new=AsyncMock()) as mock_index,
    ):
        await init_collections()

    indexed_fields = {call.kwargs["field_name"] for call in mock_index.call_args_list}
    assert indexed_fields == {"ticker", "section"}
    for call in mock_index.call_args_list:
        assert call.kwargs["collection_name"] == FILINGS_COLLECTION


# ---------------------------------------------------------------------------
# upsert_chunks
# ---------------------------------------------------------------------------

async def test_upsert_chunks_builds_points_with_hex_id_and_full_payload():
    chunk = make_chunk(chunk_id="00000000000000ff")
    vector = [0.1, 0.2, 0.3]

    with patch("app.clients.qdrant._client.upsert", new=AsyncMock()) as mock_upsert:
        await upsert_chunks([(chunk, vector)])

    call = mock_upsert.call_args
    assert call.kwargs["collection_name"] == FILINGS_COLLECTION
    points = call.kwargs["points"]
    assert len(points) == 1
    point = points[0]
    assert point.id == int("00000000000000ff", 16)
    assert point.vector == vector
    assert point.payload == {
        "chunk_id": chunk.chunk_id,
        "text": chunk.text,
        "ticker": chunk.ticker,
        "section": chunk.section,
        "year": chunk.year,
        "source_url": chunk.source_url,
    }


async def test_upsert_chunks_empty_list_still_calls_upsert_with_no_points():
    with patch("app.clients.qdrant._client.upsert", new=AsyncMock()) as mock_upsert:
        await upsert_chunks([])

    assert mock_upsert.call_args.kwargs["points"] == []


# ---------------------------------------------------------------------------
# query_dense
# ---------------------------------------------------------------------------

def make_search_result(chunk: Chunk, score: float):
    return SimpleNamespace(
        score=score,
        payload={
            "chunk_id": chunk.chunk_id, "text": chunk.text, "ticker": chunk.ticker,
            "section": chunk.section, "year": chunk.year, "source_url": chunk.source_url,
        },
    )


def make_query_response(points: list):
    return SimpleNamespace(points=points)


async def test_query_dense_maps_results_to_chunks_with_score():
    chunk = make_chunk()
    with patch(
        "app.clients.qdrant._client.query_points",
        new=AsyncMock(return_value=make_query_response([make_search_result(chunk, 0.87)])),
    ):
        results = await query_dense([0.1, 0.2], ticker="AAPL")

    assert len(results) == 1
    assert results[0].chunk_id == chunk.chunk_id
    assert results[0].score == 0.87


async def test_query_dense_filters_by_ticker_only_without_section():
    with patch(
        "app.clients.qdrant._client.query_points", new=AsyncMock(return_value=make_query_response([]))
    ) as mock_query:
        await query_dense([0.1, 0.2], ticker="AAPL")

    query_filter = mock_query.call_args.kwargs["query_filter"]
    assert len(query_filter.must) == 1
    assert query_filter.must[0].key == "ticker"


async def test_query_dense_adds_section_filter_when_given():
    with patch(
        "app.clients.qdrant._client.query_points", new=AsyncMock(return_value=make_query_response([]))
    ) as mock_query:
        await query_dense([0.1, 0.2], ticker="AAPL", section="Item 1A")

    query_filter = mock_query.call_args.kwargs["query_filter"]
    keys = {c.key for c in query_filter.must}
    assert keys == {"ticker", "section"}


async def test_query_dense_passes_limit_through():
    with patch(
        "app.clients.qdrant._client.query_points", new=AsyncMock(return_value=make_query_response([]))
    ) as mock_query:
        await query_dense([0.1, 0.2], ticker="AAPL", limit=3)

    assert mock_query.call_args.kwargs["limit"] == 3


async def test_query_dense_passes_vector_as_query_kwarg():
    vector = [0.1, 0.2, 0.3]
    with patch(
        "app.clients.qdrant._client.query_points", new=AsyncMock(return_value=make_query_response([]))
    ) as mock_query:
        await query_dense(vector, ticker="AAPL")

    assert mock_query.call_args.kwargs["query"] == vector
