"""
Embeds text with OpenAI text-embedding-3-small.

Public API:
    embed_texts(texts: list[str])   -> list[list[float]]
    embed_chunks(chunks: list[Chunk]) -> list[tuple[Chunk, list[float]]]

Both functions batch inputs in groups of 100 and send batches concurrently.
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


async def _embed_batch_texts(batch: list[str]) -> list[list[float]]:
    try:
        response = await _client.embeddings.create(input=batch, model=MODEL)
    except openai.APIError as exc:
        raise EmbedderError(f"OpenAI embeddings API error: {exc}") from exc
    return [item.embedding for item in response.data]


async def embed_texts(texts: list[str]) -> list[list[float]]:
    """Return one 1536-dim embedding vector per input string.

    Texts are split into batches of 100 and sent concurrently.
    """
    batches = [texts[i : i + BATCH_SIZE] for i in range(0, len(texts), BATCH_SIZE)]
    results = await asyncio.gather(*(_embed_batch_texts(b) for b in batches))
    return [vec for batch in results for vec in batch]


async def embed_chunks(chunks: list[Chunk]) -> list[tuple[Chunk, list[float]]]:
    """Return each Chunk paired with its embedding vector.

    Delegates to embed_texts — the Chunk objects are passed through unchanged.
    """
    vectors = await embed_texts([c.text for c in chunks])
    return list(zip(chunks, vectors))
