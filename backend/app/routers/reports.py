"""
Reports router: read-only access to completed ResearchReports and raw chunks.

Routes
------
GET /reports              — list reports, optionally filtered by ticker
GET /reports/{report_id}  — single report by ID (the session_id that produced it)
GET /chunks/{chunk_id}    — raw chunk text + metadata by chunk_id (for CitationDrawer)
"""

from typing import Annotated

from fastapi import APIRouter, HTTPException, Path, Query

from app.clients import qdrant as qdrant_client
from app.models.chunk import Chunk
from app.models.report import ResearchReport

router = APIRouter()


@router.get("/reports", response_model=list[ResearchReport])
async def list_reports(
    ticker: Annotated[str | None, Query(
        description="Ticker symbol to filter by. Required: returns [] without it.",
        json_schema_extra={"example": "AAPL"},
    )] = None,
    limit: Annotated[int, Query(
        description="Maximum number of reports to return.",
        ge=1, le=50,
        json_schema_extra={"example": 10},
    )] = 10,
) -> list[ResearchReport]:
    """Return completed research reports for a ticker, oldest first.

    Pass ?ticker=AAPL to scope results to a single company. Without a ticker
    filter the endpoint returns an empty list — full collection scans on the
    Qdrant free tier are expensive and not needed for the core demo flow.
    """
    if not ticker:
        return []
    return await qdrant_client.get_reports_for_ticker(ticker.upper(), limit=limit)


@router.get("/reports/{report_id}", response_model=ResearchReport)
async def get_report(
    report_id: Annotated[str, Path(
        description="The session_id from POST /analyze (same value as report_id in the done SSE event).",
        json_schema_extra={"example": "3fa85f64-5717-4562-b3fc-2c963f66afa6"},
    )],
) -> ResearchReport:
    """Return a single ResearchReport by its report_id.

    The frontend calls this after the SSE stream emits a `done` event — it reads
    `report_id` from that event and fetches the full report here.
    """
    report = await qdrant_client.get_report_by_id(report_id)
    if report is None:
        raise HTTPException(status_code=404, detail=f"Report {report_id!r} not found")
    return report


@router.get("/chunks/{chunk_id}", response_model=Chunk)
async def get_chunk(
    chunk_id: Annotated[str, Path(
        description="16-character hex string from a Claim's chunk_id in a ResearchReport. Paste from bull_case[0].chunk_id or bear_case[0].chunk_id.",
        json_schema_extra={"example": "a1b2c3d4e5f6a7b8"},
    )],
) -> Chunk:
    """Return the raw 10-K passage and metadata for a chunk_id.

    The frontend CitationDrawer calls this when the user clicks a citation badge
    in the ReportDisplay — it shows the exact SEC filing passage that backs the claim.
    chunk_id is null for web-search-derived claims; don't call this endpoint for those.
    """
    chunk = await qdrant_client.get_chunk_by_id(chunk_id)
    if chunk is None:
        raise HTTPException(status_code=404, detail=f"Chunk {chunk_id!r} not found")
    return chunk
