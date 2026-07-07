"""
Hybrid retrieval: BM25 + Qdrant dense search fused with RRF, then Cohere reranked.

Public API:
    retrieve(query, ticker, top_k=5, section=None) -> list[Chunk]

Pipeline per call:
    1. Embed query with text-embedding-3-small
    2. Qdrant dense search — top 20 candidates
    3. BM25 over those candidates (CPU-bound, run in thread)
    4. RRF fusion: score = Σ 1 / (60 + rank) across both ranked lists
    5. Cohere rerank: top 20 fused → top_k final results
"""

import asyncio

from rank_bm25 import BM25Okapi

from app.clients import cohere as cohere_client
from app.clients import qdrant as qdrant_client
from app.models.chunk import Chunk
from app.rag.embedder import embed_texts

CANDIDATE_LIMIT = 20
RRF_K = 60


def _bm25_rank(query: str, chunks: list[Chunk]) -> list[Chunk]:
    tokenized_corpus = [c.text.lower().split() for c in chunks]
    bm25 = BM25Okapi(tokenized_corpus)
    scores = bm25.get_scores(query.lower().split())
    ranked = sorted(zip(chunks, scores), key=lambda x: x[1], reverse=True)
    return [c.model_copy(update={"score": float(s)}) for c, s in ranked]


def _rrf(ranked_lists: list[list[Chunk]]) -> list[Chunk]:
    scores: dict[str, float] = {}
    by_id: dict[str, Chunk] = {}
    for ranked in ranked_lists:
        for rank, chunk in enumerate(ranked):
            scores[chunk.chunk_id] = scores.get(chunk.chunk_id, 0.0) + 1.0 / (RRF_K + rank)
            by_id[chunk.chunk_id] = chunk
    return [
        by_id[cid].model_copy(update={"score": s})
        for cid, s in sorted(scores.items(), key=lambda x: x[1], reverse=True)
    ]


async def retrieve(
    query: str,
    ticker: str,
    top_k: int = 5,
    section: str | None = None,
) -> list[Chunk]:
    """Return the top `top_k` chunks most relevant to `query` for the given ticker."""
    query_vector = (await embed_texts([query]))[0]

    dense_candidates = await qdrant_client.query_dense(
        vector=query_vector,
        ticker=ticker,
        limit=CANDIDATE_LIMIT,
        section=section,
    )

    if not dense_candidates:
        return []

    bm25_ranked = await asyncio.to_thread(_bm25_rank, query, dense_candidates)
    dense_ranked = sorted(dense_candidates, key=lambda c: c.score, reverse=True)

    fused = _rrf([bm25_ranked, dense_ranked])

    return await cohere_client.rerank(query, fused, top_n=top_k)
