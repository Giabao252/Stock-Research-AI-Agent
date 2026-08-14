"""
Qdrant client: collection management, chunk upsert, dense vector search,
and report storage/retrieval.

Public API — filings collection:
    init_collections()                                         -> None
    upsert_chunks(pairs: list[tuple[Chunk, list[float]]])     -> None
    query_dense(vector, ticker, limit, section)                -> list[Chunk]
    get_chunk_by_id(chunk_id: str)                            -> Chunk | None

Public API — reports collection:
    store_report(report_id: str, report: ResearchReport)      -> None
    get_reports_for_ticker(ticker, limit)                     -> list[ResearchReport]
    get_report_by_id(report_id: str)                          -> ResearchReport | None
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
from app.models.report import ResearchReport

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


def _chunk_from_payload(payload: dict, score: float = 0.0) -> Chunk:
    return Chunk(
        chunk_id=payload["chunk_id"],
        text=payload["text"],
        ticker=payload["ticker"],
        section=payload["section"],
        year=payload["year"],
        source_url=payload["source_url"],
        score=score,
    )


async def get_chunk_by_id(chunk_id: str) -> Chunk | None:
    """Return a single Chunk from the filings collection by its chunk_id, or None."""
    point_id = int(chunk_id, 16)
    results = await _client.retrieve(
        collection_name=FILINGS_COLLECTION,
        ids=[point_id],
        with_payload=True,
    )
    if not results:
        return None
    return _chunk_from_payload(results[0].payload)


# ---------------------------------------------------------------------------
# Reports collection — payload-only storage (zero vector, filter via scroll)
# ---------------------------------------------------------------------------

_ZERO_VECTOR = [0.0] * VECTOR_SIZE


async def store_report(report_id: str, report: ResearchReport) -> None:
    """Upsert a completed ResearchReport into the reports collection.

    Reports have no natural embedding — we store them payload-only with a zero
    vector and retrieve them via scroll + payload filter. The report_id (which is
    the session_id) is stored both as the point's UUID ID and as a payload field
    so scroll-based lookups can filter on it without needing to know the point ID.
    """
    payload = report.model_dump(mode="json")  # datetime → ISO string, safe for Qdrant
    payload["report_id"] = report_id

    await _client.upsert(
        collection_name=REPORTS_COLLECTION,
        points=[
            PointStruct(
                id=report_id,       # UUID string — Qdrant accepts UUID-format strings
                vector=_ZERO_VECTOR,
                payload=payload,
            )
        ],
    )


async def get_reports_for_ticker(ticker: str, limit: int = 5) -> list[ResearchReport]:
    """Return up to `limit` reports for the given ticker, oldest first.

    Ordered oldest-first so build_system_prompt can append them as "prior reports
    (most recent last)" and the agent reads the trajectory correctly.
    """
    results, _ = await _client.scroll(
        collection_name=REPORTS_COLLECTION,
        scroll_filter=Filter(
            must=[FieldCondition(key="ticker", match=MatchValue(value=ticker))]
        ),
        limit=limit,
        with_payload=True,
        with_vectors=False,
    )
    reports = [ResearchReport.model_validate(r.payload) for r in results]
    reports.sort(key=lambda r: r.generated_at)
    return reports


async def get_report_by_id(report_id: str) -> ResearchReport | None:
    """Return a single ResearchReport by report_id, or None if not found."""
    results, _ = await _client.scroll(
        collection_name=REPORTS_COLLECTION,
        scroll_filter=Filter(
            must=[FieldCondition(key="report_id", match=MatchValue(value=report_id))]
        ),
        limit=1,
        with_payload=True,
        with_vectors=False,
    )
    if not results:
        return None
    return ResearchReport.model_validate(results[0].payload)
