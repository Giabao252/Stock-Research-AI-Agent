"""
Agent SDK query() wrapper: builds ClaudeAgentOptions, wires hooks, drains query()
into the StreamEvent discriminated union, and runs one-shot follow-up questions.

Public API:
    run_analysis(ticker, session_id=None, prior_reports=None) -> AsyncIterator[StreamEvent]
    answer_question(question, ticker, session_id)             -> Answer
"""

import asyncio
import logging
import uuid
from datetime import datetime, timezone
from typing import AsyncIterator

from claude_agent_sdk import (
    AssistantMessage,
    ClaudeAgentOptions,
    HookMatcher,
    ResultMessage,
    SystemMessage,
    TextBlock,
    ToolUseBlock,
    query,
)

from app.agent.hooks import CitationTracker, make_post_tool_use_hook, make_pre_tool_use_hook
from app.agent.prompts import build_followup_prompt, build_system_prompt
from app.clients import redis as redis_client
from app.config import settings
from app.models.api import Answer
from app.models.report import Claim, ResearchReport
from app.models.session import DoneEvent, ErrorEvent, ObserveEvent, SessionState, StreamEvent, ThoughtEvent, ToolCallEvent

logger = logging.getLogger(__name__)

MCP_SERVER_NAME = "stock-research"
_SENTINEL = object()

# Built-in web tools would let the agent bypass the MCP tools (and their citations)
# if the MCP server is unreachable — research must only come from MCP tools.
_DISALLOWED_TOOLS = ["WebSearch", "WebFetch"]


class RunnerError(Exception):
    """Raised when answer_question fails to produce a usable result."""


def _mcp_servers() -> dict:
    return {MCP_SERVER_NAME: {"type": "http", "url": settings.mcp_server_url}}


def _mcp_connection_error(message: SystemMessage) -> str | None:
    """Return an error string if the init message reports our MCP server as unusable."""
    if message.subtype != "init":
        return None
    for server in message.data.get("mcp_servers", []):
        if server.get("name") != MCP_SERVER_NAME:
            continue
        status = server.get("status")
        if status != "connected":
            logger.warning("MCP server %r status=%s error=%s", MCP_SERVER_NAME, status, server.get("error"))
        if status in ("failed", "needs-auth"):
            detail = server.get("error") or status
            return f"MCP server '{MCP_SERVER_NAME}' is unavailable: {detail}"
    return None


def _translate_assistant_message(message: AssistantMessage) -> list[StreamEvent]:
    events: list[StreamEvent] = []
    for block in message.content:
        if isinstance(block, TextBlock):
            events.append(ThoughtEvent(content=block.text))
        elif isinstance(block, ToolUseBlock):
            events.append(ToolCallEvent(tool=block.name, args=block.input))
    return events


async def _load_or_init_session(session_id: str, ticker: str) -> SessionState:
    existing = await redis_client.get_session(session_id)
    if existing is not None:
        return existing
    return SessionState(
        session_id=session_id,
        ticker=ticker,
        status="running",
        messages=[],
        partial_report=None,
        error_message=None,
        created_at=datetime.utcnow(),
    )


def _is_grounded(claim: Claim, citation_tracker: CitationTracker) -> bool:
    if claim.chunk_id is not None:
        return citation_tracker.chunk_sources.get(claim.chunk_id) == claim.source_url
    return claim.source_url in citation_tracker.seen_urls


async def _handle_result(
    message: ResultMessage,
    session_id: str,
    ticker: str,
    citation_tracker: CitationTracker,
    event_queue: "asyncio.Queue",
) -> None:
    session = await _load_or_init_session(session_id, ticker)

    if message.is_error or message.structured_output is None:
        error_text = message.result or "Agent run failed with no structured result"
        session.status = "error"
        session.error_message = error_text
        await redis_client.save_session(session)
        await event_queue.put(ErrorEvent(message=error_text))
        return

    report = ResearchReport.model_validate(message.structured_output)
    ungrounded = [c for c in report.bull_case + report.bear_case if not _is_grounded(c, citation_tracker)]

    # metrics and generated_at are owned by the server, not the model: the model may
    # fill them from web-search snippets or invent a timestamp.
    metrics = citation_tracker.stock_metrics or {}
    reasons = []
    if ungrounded:
        reasons.append(f"{len(ungrounded)} claim(s) could not be verified against retrieved chunks")
    if not metrics:
        reasons.append("stock_data_tool returned no data, so market metrics are unavailable")

    update: dict = {"metrics": metrics, "generated_at": datetime.now(timezone.utc)}
    if reasons and not report.partial:
        update.update(partial=True, partial_reason="; ".join(reasons))
    report = report.model_copy(update=update)

    session.status = "done"
    session.partial_report = report
    await redis_client.save_session(session)
    await event_queue.put(DoneEvent(report_id=session_id))


async def run_analysis(
    ticker: str,
    session_id: str | None = None,
    prior_reports: list[ResearchReport] | None = None,
) -> AsyncIterator[StreamEvent]:
    session_id = session_id or str(uuid.uuid4())
    event_queue: "asyncio.Queue" = asyncio.Queue()
    citation_tracker = CitationTracker()

    options = ClaudeAgentOptions(
        model=settings.claude_model,
        system_prompt=build_system_prompt(ticker, prior_reports),
        mcp_servers=_mcp_servers(),
        allowed_tools=[f"mcp__{MCP_SERVER_NAME}__*"],
        disallowed_tools=_DISALLOWED_TOOLS,
        output_format={"type": "json_schema", "schema": ResearchReport.model_json_schema()},
        max_budget_usd=0.50,
        hooks={
            "PreToolUse": [HookMatcher(hooks=[make_pre_tool_use_hook()])],
            "PostToolUse": [HookMatcher(hooks=[make_post_tool_use_hook(event_queue, citation_tracker)])],
        },
    )

    async def _drain() -> None:
        try:
            async for message in query(
                prompt=f"Research {ticker} and produce a bull/bear ResearchReport.",
                options=options,
            ):
                if isinstance(message, SystemMessage):
                    mcp_error = _mcp_connection_error(message)
                    if mcp_error:
                        await event_queue.put(ErrorEvent(message=mcp_error))
                        break
                elif isinstance(message, AssistantMessage):
                    for event in _translate_assistant_message(message):
                        await event_queue.put(event)
                elif isinstance(message, ResultMessage):
                    await _handle_result(message, session_id, ticker, citation_tracker, event_queue)
        except Exception as exc:
            await event_queue.put(ErrorEvent(message=str(exc)))
        finally:
            await event_queue.put(_SENTINEL)

    task = asyncio.create_task(_drain())
    try:
        while True:
            event = await event_queue.get()
            if event is _SENTINEL:
                break
            yield event
    finally:
        await task


async def answer_question(question: str, ticker: str, session_id: str) -> Answer:
    session = await redis_client.get_session(session_id)
    if session is None:
        raise RunnerError(f"Session {session_id} not found")

    citation_tracker = CitationTracker()
    # No SSE stream for /ask, so this queue only exists to satisfy
    # make_post_tool_use_hook's signature — nothing drains it.
    unused_queue: "asyncio.Queue" = asyncio.Queue()

    options = ClaudeAgentOptions(
        model=settings.claude_model,
        mcp_servers=_mcp_servers(),
        allowed_tools=[f"mcp__{MCP_SERVER_NAME}__*"],
        disallowed_tools=_DISALLOWED_TOOLS,
        output_format={"type": "json_schema", "schema": Answer.model_json_schema()},
        max_budget_usd=0.50,
        hooks={
            "PreToolUse": [HookMatcher(hooks=[make_pre_tool_use_hook()])],
            "PostToolUse": [HookMatcher(hooks=[make_post_tool_use_hook(unused_queue, citation_tracker)])],
        },
    )

    prompt = build_followup_prompt(question, ticker, session.messages)

    result: ResultMessage | None = None
    async for message in query(prompt=prompt, options=options):
        if isinstance(message, ResultMessage):
            result = message

    if result is None or result.is_error or result.structured_output is None:
        detail = result.result if result else "no result message"
        raise RunnerError(f"Failed to answer question for {ticker}: {detail}")

    answer = Answer.model_validate(result.structured_output)
    grounded_sources = [s for s in answer.sources if _is_grounded(s, citation_tracker)]
    answer = answer.model_copy(update={"sources": grounded_sources})

    await redis_client.append_message(session_id, "user", question)
    await redis_client.append_message(session_id, "assistant", answer.text)

    return answer
