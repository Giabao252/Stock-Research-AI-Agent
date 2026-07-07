"""
Cohere reranker client: reorders a candidate list by semantic relevance.

Public API:
    rerank(query, chunks, top_n=5) -> list[Chunk]

Uses the Cohere Rerank v2 API directly over httpx — no cohere SDK needed.
The returned list is truncated to top_n and each Chunk.score is replaced
with the Cohere relevance_score (0.0–1.0).
"""

import httpx

from app.config import settings
from app.models.chunk import Chunk

RERANK_URL = "https://api.cohere.com/v2/rerank"
MODEL = "rerank-english-v3.0"

http_client = httpx.AsyncClient(
    headers={
        "Authorization": f"bearer {settings.cohere_api_key}",
        "Content-Type": "application/json",
    },
    timeout=httpx.Timeout(30.0),
)


class CohereError(Exception):
    """Raised when the Cohere rerank API call fails."""


async def post_rerank(payload: dict) -> list[dict]:
    try:
        response = await http_client.post(RERANK_URL, json=payload)
        response.raise_for_status()
    except httpx.HTTPStatusError as exc:
        raise CohereError(
            f"Cohere rerank API error (HTTP {exc.response.status_code}): {exc.response.text}"
        ) from exc
    return response.json()["results"]


async def rerank(query: str, chunks: list[Chunk], top_n: int = 5) -> list[Chunk]:
    """Rerank `chunks` by relevance to `query` using Cohere, returning the top `top_n`.

    Each returned Chunk has its .score replaced with Cohere's relevance_score (0–1).
    If the chunk list is empty, returns an empty list immediately.
    """
    if not chunks:
        return []

    top_n = min(top_n, len(chunks))

    results = await post_rerank(
        {
            "model": MODEL,
            "query": query,
            "documents": [c.text for c in chunks],
            "top_n": top_n,
            "return_documents": False,
        }
    )

    return [
        chunks[r["index"]].model_copy(update={"score": r["relevance_score"]})
        for r in results
    ]
