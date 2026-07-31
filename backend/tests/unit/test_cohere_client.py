"""
Unit tests for clients/cohere.py.
"""

from unittest.mock import AsyncMock, MagicMock, patch

import httpx
import pytest

from app.clients.cohere import CohereError, post_rerank, rerank
from app.models.chunk import Chunk


def make_chunk(chunk_id: str, text: str) -> Chunk:
    return Chunk(
        chunk_id=chunk_id, text=text, ticker="AAPL", section="Item 1A",
        year=2024, source_url="https://sec.gov/test", score=0.0,
    )


# ---------------------------------------------------------------------------
# rerank
# ---------------------------------------------------------------------------

async def test_rerank_empty_chunks_short_circuits_no_network_call():
    with patch("app.clients.cohere.post_rerank", new=AsyncMock()) as mock_post:
        result = await rerank("query", [])

    assert result == []
    mock_post.assert_not_awaited()


async def test_rerank_clamps_top_n_to_chunk_count():
    chunks = [make_chunk("a", "text a"), make_chunk("b", "text b")]
    with patch(
        "app.clients.cohere.post_rerank",
        new=AsyncMock(return_value=[{"index": 0, "relevance_score": 0.9}, {"index": 1, "relevance_score": 0.5}]),
    ) as mock_post:
        await rerank("query", chunks, top_n=10)

    payload = mock_post.call_args[0][0]
    assert payload["top_n"] == 2


async def test_rerank_reorders_and_replaces_score():
    chunks = [make_chunk("a", "text a"), make_chunk("b", "text b"), make_chunk("c", "text c")]
    # Cohere says c is most relevant, then a
    with patch(
        "app.clients.cohere.post_rerank",
        new=AsyncMock(return_value=[{"index": 2, "relevance_score": 0.95}, {"index": 0, "relevance_score": 0.6}]),
    ):
        result = await rerank("query", chunks, top_n=2)

    assert [c.chunk_id for c in result] == ["c", "a"]
    assert result[0].score == 0.95
    assert result[1].score == 0.6


# ---------------------------------------------------------------------------
# post_rerank
# ---------------------------------------------------------------------------

async def test_post_rerank_returns_results_list():
    resp = MagicMock()
    resp.json.return_value = {"results": [{"index": 0, "relevance_score": 0.9}]}
    resp.raise_for_status = MagicMock()
    with patch("app.clients.cohere.http_client.post", new=AsyncMock(return_value=resp)):
        results = await post_rerank({"query": "q"})

    assert results == [{"index": 0, "relevance_score": 0.9}]


async def test_post_rerank_raises_cohere_error_on_http_failure():
    request = httpx.Request("POST", "https://api.cohere.com/v2/rerank")
    response = httpx.Response(401, request=request, text="unauthorized")
    error = httpx.HTTPStatusError("error", request=request, response=response)

    mock_response = MagicMock()
    mock_response.raise_for_status.side_effect = error

    with patch("app.clients.cohere.http_client.post", new=AsyncMock(return_value=mock_response)):
        with pytest.raises(CohereError):
            await post_rerank({"query": "q"})
