"""
Embeds a list of Chunk objects with OpenAI text-embedding-3-small.

Public API:
    embed_chunks(chunks: list[Chunk]) -> list[tuple[Chunk, list[float]]]

Async and network-bound — no asyncio.to_thread() needed.
Chunks are sent in batches of 100 to stay within the OpenAI embeddings API limits.
"""

import asyncio

import openai
from openai import AsyncOpenAI

from app.config import settings
from app.models.chunk import Chunk

BATCH_SIZE = 100
MODEL = "text-embedding-3-small"

_client = AsyncOpenAI(api_key=settings.openai_api_key)


class EmbedderError(Exception):
    """Raised when the OpenAI embeddings API call fails."""


async def _embed_batch(batch: list[Chunk]) -> list[tuple[Chunk, list[float]]]:
    try:
        response = await _client.embeddings.create(
            input=[c.text for c in batch],
            model=MODEL,
        )
    except openai.APIError as exc:
        raise EmbedderError(f"OpenAI embeddings API error: {exc}") from exc

    return [(chunk, item.embedding) for chunk, item in zip(batch, response.data)]


async def embed_chunks(chunks: list[Chunk]) -> list[tuple[Chunk, list[float]]]:
    """Return each Chunk paired with its 1536-dim embedding vector.

    Batches are sent concurrently via asyncio.gather.
    """
    batches = [chunks[i : i + BATCH_SIZE] for i in range(0, len(chunks), BATCH_SIZE)]
    results = await asyncio.gather(*(_embed_batch(b) for b in batches))
    return [pair for batch_result in results for pair in batch_result]
