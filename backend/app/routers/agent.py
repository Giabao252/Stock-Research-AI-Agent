"""
Agent router: SSE stream for live reasoning chain + follow-up Q&A.

Routes
------
GET  /sessions/{session_id}/stream — hold-open SSE, streams StreamEvent until done/error
POST /ask                          — one-shot follow-up question, returns Answer
"""

from typing import Annotated

from fastapi import APIRouter, HTTPException, Path
from fastapi.responses import StreamingResponse

from app.agent.runner import RunnerError, answer_question, run_analysis
from app.clients import qdrant as qdrant_client
from app.clients import redis as redis_client
from app.models.api import Answer, AskRequest
from app.models.session import DoneEvent, ErrorEvent

router = APIRouter()

_SESSION_ID_PARAM = Path(
    description="The session_id returned by POST /analyze",
    json_schema_extra={"example": "3fa85f64-5717-4562-b3fc-2c963f66afa6"},
)

# SSE headers that tell Railway's nginx proxy not to buffer the stream.
# Without X-Accel-Buffering: no, nginx accumulates chunks and the client
# sees nothing until the run finishes — killing the live-chain effect.
_SSE_HEADERS = {
    "Cache-Control": "no-cache",
    "X-Accel-Buffering": "no",
    "Connection": "keep-alive",
}


@router.get("/sessions/{session_id}/stream")
async def stream(
    session_id: Annotated[str, _SESSION_ID_PARAM],
) -> StreamingResponse:
    """Stream the live reasoning chain for an in-progress analysis session.

    Opens the Agent SDK run, translates every AssistantMessage / hook callback
    into a StreamEvent, and yields it as an SSE `data:` line. On DoneEvent the
    completed ResearchReport is persisted to Qdrant and the Redis session is
    cleared. On ErrorEvent the Redis session is also cleared.

    The agent run starts when this connection opens — POST /analyze only creates
    the session record and returns the session_id; it does not start the agent.
    """
    session = await redis_client.get_session(session_id)
    if session is None:
        raise HTTPException(status_code=404, detail=f"Session {session_id} not found")

    # Load prior reports so the system prompt can note verdict trajectory.
    # Cheap read — at most 5 small payloads from Qdrant.
    prior_reports = await qdrant_client.get_reports_for_ticker(session.ticker)

    async def event_generator():
        async for event in run_analysis(session.ticker, session_id, prior_reports):
            yield f"data: {event.model_dump_json()}\n\n"

            if isinstance(event, DoneEvent):
                # runner._handle_result already saved session.partial_report to Redis;
                # read it back, persist to Qdrant for GET /reports/{id}, then clear Redis.
                updated = await redis_client.get_session(session_id)
                if updated and updated.partial_report:
                    await qdrant_client.store_report(session_id, updated.partial_report)
                await redis_client.delete_session(session_id)

            elif isinstance(event, ErrorEvent):
                await redis_client.delete_session(session_id)

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers=_SSE_HEADERS,
    )


@router.post("/ask", response_model=Answer)
async def ask(body: AskRequest) -> Answer:
    """Answer a follow-up question about a ticker using the session's conversation buffer.

    The session must exist in Redis (i.e. the analysis must still be in progress or
    have finished without being cleared). Returns a grounded Answer with sources.
    """
    try:
        return await answer_question(body.question, body.ticker, body.session_id)
    except RunnerError as exc:
        raise HTTPException(status_code=404, detail=str(exc))
