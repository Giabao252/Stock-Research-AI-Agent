"""
Gateway router: session lifecycle + health check.

POST   /analyze              — validate ticker, create Redis session, return session_id
DELETE /sessions/{session_id} — cancel / clean up a session
GET    /health               — liveness probe for Railway
"""

import uuid
from datetime import datetime

from fastapi import APIRouter, HTTPException

from app.clients import redis as redis_client
from app.config import settings
from app.models.api import AnalyzeRequest, AnalyzeResponse
from app.models.session import SessionState

router = APIRouter()


@router.post("/analyze", response_model=AnalyzeResponse, status_code=202)
async def analyze(body: AnalyzeRequest) -> AnalyzeResponse:
    """Create a research session for `ticker` and return the session_id.

    The caller should immediately open GET /sessions/{session_id}/stream to receive
    the live reasoning chain. The agent run starts when that SSE connection is opened,
    not here — this endpoint only initialises the session record in Redis.
    """
    session_id = str(uuid.uuid4())

    session = SessionState(
        session_id=session_id,
        ticker=body.ticker.upper(),
        status="running",
        messages=[],
        partial_report=None,
        error_message=None,
        created_at=datetime.utcnow(),
    )
    await redis_client.save_session(session)

    return AnalyzeResponse(session_id=session_id, ticker=session.ticker)


@router.delete("/sessions/{session_id}", status_code=204)
async def delete_session(session_id: str) -> None:
    """Delete a session record from Redis.

    Idempotent — returns 204 even if the session was already gone or expired.
    The frontend calls this when the user navigates away mid-stream so stale
    session keys don't accumulate in the Upstash free tier.
    """
    await redis_client.delete_session(session_id)


@router.get("/health")
async def health() -> dict:
    """Liveness probe. Railway checks this path before marking the deploy healthy."""
    return {"status": "ok", "model": settings.claude_model}
