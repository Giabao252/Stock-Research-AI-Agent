"""
Qdrant client: collection management, chunk upsert, and dense vector search.

Public API:
    init_collections()                                     -> None
    upsert_chunks(pairs: list[tuple[Chunk, list[float]]]) -> None
    query_dense(vector, ticker, limit, section)            -> list[Chunk]
"""

from qdrant_client import AsyncQdrantClient
from qdrant_client.models import (
    Distance,
    FieldCondition,
    Filter,
    MatchValue,
    PayloadSchemaType,
    PointStruct,
    VectorParams,
)

from app.config import settings
from app.models.chunk import Chunk

FILINGS_COLLECTION = "filings"
REPORTS_COLLECTION = "reports"
VECTOR_SIZE = 1536  # text-embedding-3-small dimensions

_client = AsyncQdrantClient(
    url=settings.qdrant_url,
    api_key=settings.qdrant_api_key or None,  # None disables auth for local Docker
)


async def init_collections() -> None:
    """Create filings and reports collections if they don't already exist.

    Also ensures payload indexes exist on "ticker" and "section" — Qdrant Cloud's
    strict mode rejects filtering on an unindexed field, and query_dense() filters
    on both. Index creation is idempotent, so this runs unconditionally on every
    call (not just when the collection is first created) to self-heal collections
    created before these indexes existed.
    """
    existing = {c.name for c in (await _client.get_collections()).collections}

    if FILINGS_COLLECTION not in existing:
        await _client.create_collection(
            collection_name=FILINGS_COLLECTION,
            vectors_config=VectorParams(size=VECTOR_SIZE, distance=Distance.COSINE),
        )

    if REPORTS_COLLECTION not in existing:
        await _client.create_collection(
            collection_name=REPORTS_COLLECTION,
            vectors_config=VectorParams(size=VECTOR_SIZE, distance=Distance.COSINE),
        )

    for field_name in ("ticker", "section"):
        await _client.create_payload_index(
            collection_name=FILINGS_COLLECTION,
            field_name=field_name,
            field_schema=PayloadSchemaType.KEYWORD,
        )


async def upsert_chunks(pairs: list[tuple[Chunk, list[float]]]) -> None:
    """Upsert chunk embeddings into the filings collection.

    chunk_id is a 16-char hex string (64-bit) used as the point ID — re-ingesting
    the same filing overwrites existing points rather than duplicating them.
    """
    points = [
        PointStruct(
            id=int(chunk.chunk_id, 16),
            vector=vector,
            payload={
                "chunk_id": chunk.chunk_id,
                "text": chunk.text,
                "ticker": chunk.ticker,
                "section": chunk.section,
                "year": chunk.year,
                "source_url": chunk.source_url,
            },
        )
        for chunk, vector in pairs
    ]
    await _client.upsert(collection_name=FILINGS_COLLECTION, points=points)


async def query_dense(
    vector: list[float],
    ticker: str,
    limit: int = 20,
    section: str | None = None,
) -> list[Chunk]:
    """Return the top `limit` chunks by cosine similarity, filtered by ticker.

    Optionally narrows results to a specific 10-K section (e.g. "Item 1A").
    The retrieval score from Qdrant is written to Chunk.score for RRF fusion.
    """
    conditions = [FieldCondition(key="ticker", match=MatchValue(value=ticker))]
    if section:
        conditions.append(FieldCondition(key="section", match=MatchValue(value=section)))

    response = await _client.query_points(
        collection_name=FILINGS_COLLECTION,
        query=vector,
        query_filter=Filter(must=conditions),
        limit=limit,
        with_payload=True,
    )
    results = response.points

    return [
        Chunk(
            chunk_id=r.payload["chunk_id"],
            text=r.payload["text"],
            ticker=r.payload["ticker"],
            section=r.payload["section"],
            year=r.payload["year"],
            source_url=r.payload["source_url"],
            score=r.score,
        )
        for r in results
    ]
