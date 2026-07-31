"""
Unit tests for rag/embedder.py.
"""

from unittest.mock import AsyncMock, MagicMock, patch

import httpx
import openai
import pytest

from app.models.chunk import Chunk
from app.rag.embedder import EmbedderError, embed_chunks, embed_texts


def make_embedding_response(n: int):
    resp = MagicMock()
    resp.data = [MagicMock(embedding=[float(i)] * 3) for i in range(n)]
    return resp


def make_chunk(chunk_id: str) -> Chunk:
    return Chunk(
        chunk_id=chunk_id, text=f"text {chunk_id}", ticker="AAPL", section="Item 1A",
        year=2024, source_url="https://sec.gov/test", score=0.0,
    )


# ---------------------------------------------------------------------------
# embed_texts
# ---------------------------------------------------------------------------

async def test_embed_texts_batches_large_input_into_groups_of_100():
    texts = [f"text {i}" for i in range(250)]
    call_sizes = []

    async def fake_create(input, model):
        call_sizes.append(len(input))
        return make_embedding_response(len(input))

    with patch("app.rag.embedder._client.embeddings.create", new=AsyncMock(side_effect=fake_create)):
        vectors = await embed_texts(texts)

    assert len(vectors) == 250
    assert sorted(call_sizes) == [50, 100, 100]


async def test_embed_texts_small_input_single_batch():
    texts = ["a", "b", "c"]
    with patch(
        "app.rag.embedder._client.embeddings.create",
        new=AsyncMock(return_value=make_embedding_response(3)),
    ) as mock_create:
        vectors = await embed_texts(texts)

    assert len(vectors) == 3
    assert mock_create.await_count == 1


async def test_embed_texts_wraps_openai_api_error():
    request = httpx.Request("POST", "https://api.openai.com/v1/embeddings")
    error = openai.APIError("boom", request, body=None)
    with patch("app.rag.embedder._client.embeddings.create", new=AsyncMock(side_effect=error)):
        with pytest.raises(EmbedderError):
            await embed_texts(["a"])


# ---------------------------------------------------------------------------
# embed_chunks
# ---------------------------------------------------------------------------

async def test_embed_chunks_pairs_in_order():
    chunks = [make_chunk("a"), make_chunk("b")]
    with patch("app.rag.embedder._client.embeddings.create", new=AsyncMock(return_value=make_embedding_response(2))):
        pairs = await embed_chunks(chunks)

    assert len(pairs) == 2
    assert pairs[0][0] is chunks[0]
    assert pairs[1][0] is chunks[1]
    assert all(isinstance(vec, list) for _, vec in pairs)
