"""
Unit tests for rag/retrieval.py.

Pure functions (_bm25_rank, _rrf) are tested directly.
retrieve() is tested with mocked external calls (embed_texts, query_dense, rerank).
"""

from unittest.mock import AsyncMock, patch

import pytest

from app.models.chunk import Chunk
from app.rag.retrieval import _bm25_rank, _rrf, retrieve

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def make_chunk(chunk_id: str, text: str, score: float = 0.0) -> Chunk:
    return Chunk(
        chunk_id=chunk_id,
        text=text,
        ticker="AAPL",
        section="Item 1A",
        year=2024,
        source_url="https://sec.gov/test",
        score=score,
    )


CHUNKS = [
    make_chunk("aaa", "Apple faces competition risk in smartphone markets", score=0.9),
    make_chunk("bbb", "Revenue growth driven by iPhone and services segment", score=0.8),
    make_chunk("ccc", "Supply chain disruptions may impact product availability", score=0.7),
]


# ---------------------------------------------------------------------------
# _bm25_rank
# ---------------------------------------------------------------------------

def test_bm25_rank_returns_same_chunks():
    ranked = _bm25_rank("competition risk", CHUNKS)
    assert {c.chunk_id for c in ranked} == {c.chunk_id for c in CHUNKS}


def test_bm25_rank_top_result_is_relevant():
    ranked = _bm25_rank("competition risk", CHUNKS)
    # chunk "aaa" contains both "competition" and "risk"
    assert ranked[0].chunk_id == "aaa"


def test_bm25_rank_scores_are_floats():
    ranked = _bm25_rank("competition", CHUNKS)
    for chunk in ranked:
        assert isinstance(chunk.score, float)


def test_bm25_rank_empty_input():
    assert _bm25_rank("query", []) == []


# ---------------------------------------------------------------------------
# _rrf
# ---------------------------------------------------------------------------

def test_rrf_merges_two_lists():
    list_a = [make_chunk("aaa", "text a"), make_chunk("bbb", "text b")]
    list_b = [make_chunk("bbb", "text b"), make_chunk("aaa", "text a")]
    fused = _rrf([list_a, list_b])
    assert len(fused) == 2


def test_rrf_deduplicates():
    # same chunk appearing in both lists should produce one entry
    chunk = make_chunk("aaa", "text")
    fused = _rrf([[chunk], [chunk]])
    assert len(fused) == 1


def test_rrf_agreement_boosts_score():
    # "aaa" is #1 in both lists, "bbb" is #2 in both — aaa should score higher
    list_a = [make_chunk("aaa", "text a"), make_chunk("bbb", "text b")]
    list_b = [make_chunk("aaa", "text a"), make_chunk("bbb", "text b")]
    fused = _rrf([list_a, list_b])
    assert fused[0].chunk_id == "aaa"


def test_rrf_handles_disjoint_lists():
    list_a = [make_chunk("aaa", "text a")]
    list_b = [make_chunk("bbb", "text b")]
    fused = _rrf([list_a, list_b])
    assert {c.chunk_id for c in fused} == {"aaa", "bbb"}


def test_rrf_empty_lists():
    assert _rrf([[], []]) == []


# ---------------------------------------------------------------------------
# retrieve() — mocked external calls
# ---------------------------------------------------------------------------

@pytest.fixture
def mock_dense_results():
    return [
        make_chunk("aaa", "Apple faces competition risk in smartphone markets", score=0.9),
        make_chunk("bbb", "Revenue growth driven by iPhone and services segment", score=0.8),
        make_chunk("ccc", "Supply chain disruptions may impact product availability", score=0.7),
    ]


@pytest.fixture
def mock_reranked(mock_dense_results):
    # Cohere flips order: ccc → aaa → bbb
    return [
        mock_dense_results[2].model_copy(update={"score": 0.95}),
        mock_dense_results[0].model_copy(update={"score": 0.88}),
    ]


async def test_retrieve_returns_list_of_chunks(mock_dense_results, mock_reranked):
    with (
        patch("app.rag.retrieval.embed_texts", new=AsyncMock(return_value=[[0.1] * 1536])),
        patch("app.rag.retrieval.qdrant_client.query_dense", new=AsyncMock(return_value=mock_dense_results)),
        patch("app.rag.retrieval.cohere_client.rerank", new=AsyncMock(return_value=mock_reranked)),
    ):
        results = await retrieve("competition risk", ticker="AAPL", top_k=2)

    assert isinstance(results, list)
    assert all(isinstance(c, Chunk) for c in results)
    assert len(results) == 2


async def test_retrieve_returns_empty_on_no_dense_results():
    with (
        patch("app.rag.retrieval.embed_texts", new=AsyncMock(return_value=[[0.1] * 1536])),
        patch("app.rag.retrieval.qdrant_client.query_dense", new=AsyncMock(return_value=[])),
    ):
        results = await retrieve("anything", ticker="AAPL")

    assert results == []


async def test_retrieve_passes_section_filter_to_qdrant(mock_dense_results, mock_reranked):
    with (
        patch("app.rag.retrieval.embed_texts", new=AsyncMock(return_value=[[0.1] * 1536])),
        patch("app.rag.retrieval.qdrant_client.query_dense", new=AsyncMock(return_value=mock_dense_results)) as mock_qdrant,
        patch("app.rag.retrieval.cohere_client.rerank", new=AsyncMock(return_value=mock_reranked)),
    ):
        await retrieve("risk", ticker="AAPL", section="Item 1A")

    _, kwargs = mock_qdrant.call_args
    assert kwargs["section"] == "Item 1A"


async def test_retrieve_calls_cohere_with_fused_chunks(mock_dense_results, mock_reranked):
    with (
        patch("app.rag.retrieval.embed_texts", new=AsyncMock(return_value=[[0.1] * 1536])),
        patch("app.rag.retrieval.qdrant_client.query_dense", new=AsyncMock(return_value=mock_dense_results)),
        patch("app.rag.retrieval.cohere_client.rerank", new=AsyncMock(return_value=mock_reranked)) as mock_rerank,
    ):
        await retrieve("risk", ticker="AAPL", top_k=2)

    args, kwargs = mock_rerank.call_args
    assert args[0] == "risk"
    assert kwargs["top_n"] == 2
