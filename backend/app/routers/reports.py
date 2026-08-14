"""
Reports router: read-only access to completed ResearchReports and raw chunks.

Routes
------
GET /reports              — list reports, optionally filtered by ticker
GET /reports/{report_id}  — single report by ID (the session_id that produced it)
GET /chunks/{chunk_id}    — raw chunk text + metadata by chunk_id (for CitationDrawer)
"""

from fastapi import APIRouter, HTTPException, Query

from app.clients import qdrant as qdrant_client
from app.models.chunk import Chunk
from app.models.report import ResearchReport

router = APIRouter()


@router.get("/reports", response_model=list[ResearchReport])
async def list_reports(
    ticker: str | None = Query(default=None, description="Filter by ticker symbol"),
    limit: int = Query(default=10, ge=1, le=50),
) -> list[ResearchReport]:
    """Return completed research reports, newest first.

    Pass ?ticker=AAPL to scope to a single company. Without a ticker filter the
    endpoint returns an empty list — full collection scans on the Qdrant free tier
    are expensive and not needed for the core portfolio demo flow.
    """
    if not ticker:
        return []
    return await qdrant_client.get_reports_for_ticker(ticker.upper(), limit=limit)


@router.get("/reports/{report_id}", response_model=ResearchReport)
async def get_report(report_id: str) -> ResearchReport:
    """Return a single ResearchReport by its report_id (= the session_id).

    The frontend uses this after the SSE stream emits `done` — it reads
    report_id from the DoneEvent and fetches the full report here.
    """
    report = await qdrant_client.get_report_by_id(report_id)
    if report is None:
        raise HTTPException(status_code=404, detail=f"Report {report_id!r} not found")
    return report


@router.get("/chunks/{chunk_id}", response_model=Chunk)
async def get_chunk(chunk_id: str) -> Chunk:
    """Return the raw chunk text and metadata for a given chunk_id.

    The frontend CitationDrawer calls this when the user clicks a citation badge
    in the ReportDisplay — it shows the exact passage from the 10-K that backs
    the claim.
    """
    chunk = await qdrant_client.get_chunk_by_id(chunk_id)
    if chunk is None:
        raise HTTPException(status_code=404, detail=f"Chunk {chunk_id!r} not found")
    return chunk
