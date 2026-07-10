"""
MCP tool: rag_retrieval_tool

Called by the agent when it needs grounded evidence from SEC 10-K filings.
Wraps rag/retrieval.py — BM25 + Qdrant dense + RRF + Cohere reranker.
Each returned chunk carries chunk_id and source_url so the agent can
attach citations to Claim objects in the final ResearchReport.
"""

import asyncio

from fastmcp import FastMCP
from pydantic import BaseModel

from app.rag.retrieval import retrieve

mcp = FastMCP("rag-retrieval")


class ChunkSummary(BaseModel):
    chunk_id: str
    text: str
    section: str
    year: int
    source_url: str
    score: float


class RetrievalResult(BaseModel):
    query: str
    ticker: str
    chunks: list[ChunkSummary]


class ToolError(BaseModel):
    tool: str
    message: str


@mcp.tool()
async def rag_retrieval_tool(
    query: str,
    ticker: str,
    top_k: int = 5,
    section: str | None = None,
) -> RetrievalResult | ToolError:
    """Search SEC 10-K filings for chunks relevant to `query` for the given `ticker`.

    Returns up to `top_k` chunks ranked by hybrid BM25 + dense retrieval fused with RRF
    and reranked by Cohere. Each chunk includes chunk_id and source_url for citations.
    Optionally filter to a specific 10-K section (e.g. "Item 1A", "Item 7").

    If zero chunks are returned, the ticker has not been ingested yet — call
    edgar_fetch_tool first, then retry this tool with the same query.
    """
    try:
        chunks = await retrieve(query=query, ticker=ticker, top_k=top_k, section=section)
    except Exception as exc:
        return ToolError(tool="rag_retrieval_tool", message=str(exc))

    return RetrievalResult(
        query=query,
        ticker=ticker,
        chunks=[
            ChunkSummary(
                chunk_id=c.chunk_id,
                text=c.text,
                section=c.section,
                year=c.year,
                source_url=c.source_url,
                score=c.score,
            )
            for c in chunks
        ],
    )
