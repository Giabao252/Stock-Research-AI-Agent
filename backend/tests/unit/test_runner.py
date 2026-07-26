"""
Unit tests for agent/runner.py.

The Agent SDK's query() itself is never called for real — app.agent.runner.query
is patched with a real async generator function yielding real SDK dataclass
instances (AssistantMessage/ResultMessage/TextBlock/ToolUseBlock), so the
isinstance() checks inside runner.py behave exactly as they would against a
live SDK. Redis is always mocked. No network calls, no API spend.
"""

import asyncio
from datetime import datetime
from unittest.mock import AsyncMock, patch

import pytest
from claude_agent_sdk import AssistantMessage, ResultMessage, TextBlock, ToolUseBlock

from app.agent.runner import RunnerError, _handle_result, _load_or_init_session, answer_question, run_analysis
from app.models.api import Answer
from app.models.report import Claim, ResearchReport
from app.models.session import DoneEvent, ErrorEvent, SessionState, ThoughtEvent, ToolCallEvent

# ---------------------------------------------------------------------------
# Fixture helpers
# ---------------------------------------------------------------------------

def make_assistant_message(blocks, model: str = "haiku") -> AssistantMessage:
    return AssistantMessage(content=blocks, model=model)


def make_result_message(
    subtype: str = "success",
    is_error: bool = False,
    structured_output=None,
    result: str | None = None,
    session_id: str = "sdk-session-1",
) -> ResultMessage:
    return ResultMessage(
        subtype=subtype,
        duration_ms=100,
        duration_api_ms=90,
        is_error=is_error,
        num_turns=1,
        session_id=session_id,
        result=result,
        structured_output=structured_output,
    )


def make_fake_query(messages):
    async def fake_query(*, prompt, options):
        for message in messages:
            yield message

    return fake_query


def make_report(claims=None, partial=False) -> ResearchReport:
    return ResearchReport(
        ticker="AAPL",
        bull_case=claims or [],
        bear_case=[],
        verdict="bullish",
        confidence=0.7,
        tool_trace=[],
        metrics={},
        partial=partial,
        partial_reason=None,
        generated_at=datetime(2026, 1, 1),
    )


def make_session(**overrides) -> SessionState:
    base = dict(
        session_id="sess-1",
        ticker="AAPL",
        status="running",
        messages=[],
        partial_report=None,
        error_message=None,
        created_at=datetime(2026, 1, 1),
    )
    base.update(overrides)
    return SessionState(**base)


# ---------------------------------------------------------------------------
# run_analysis — message translation + event ordering
# ---------------------------------------------------------------------------

async def test_run_analysis_translates_text_and_tool_use_blocks():
    messages = [
        make_assistant_message([TextBlock(text="Let's start.")]),
        make_assistant_message([ToolUseBlock(id="tu-1", name="stock_data_tool", input={"ticker": "AAPL"})]),
        make_result_message(structured_output=make_report().model_dump()),
    ]

    with (
        patch("app.agent.runner.query", new=make_fake_query(messages)),
        patch("app.agent.runner.redis_client.get_session", new=AsyncMock(return_value=None)),
        patch("app.agent.runner.redis_client.save_session", new=AsyncMock()),
    ):
        events = [event async for event in run_analysis("AAPL", session_id="sess-1")]

    assert isinstance(events[0], ThoughtEvent)
    assert events[0].content == "Let's start."
    assert isinstance(events[1], ToolCallEvent)
    assert events[1].tool == "stock_data_tool"
    assert events[1].args == {"ticker": "AAPL"}
    assert isinstance(events[-1], DoneEvent)
    assert events[-1].report_id == "sess-1"


async def test_run_analysis_saves_report_on_success():
    report = make_report()
    messages = [make_result_message(structured_output=report.model_dump())]

    with (
        patch("app.agent.runner.query", new=make_fake_query(messages)),
        patch("app.agent.runner.redis_client.get_session", new=AsyncMock(return_value=None)),
        patch("app.agent.runner.redis_client.save_session", new=AsyncMock()) as mock_save,
    ):
        [event async for event in run_analysis("AAPL", session_id="sess-1")]

    saved_session = mock_save.call_args[0][0]
    assert saved_session.status == "done"
    assert saved_session.partial_report.verdict == "bullish"


async def test_run_analysis_yields_error_event_on_exception():
    async def fake_query(*, prompt, options):
        raise RuntimeError("connection lost")
        yield  # pragma: no cover - unreachable, keeps this an async generator function

    with patch("app.agent.runner.query", new=fake_query):
        events = [event async for event in run_analysis("AAPL", session_id="sess-1")]

    assert len(events) == 1
    assert isinstance(events[0], ErrorEvent)
    assert "connection lost" in events[0].message


# ---------------------------------------------------------------------------
# _handle_result — citation groundedness + error path
# ---------------------------------------------------------------------------

async def test_handle_result_marks_partial_when_claim_ungrounded():
    claim = Claim(text="Revenue grew", chunk_id="missing-id", source_url="https://sec.gov/x", doc_name="AAPL 10-K 2024")
    message = make_result_message(structured_output=make_report(claims=[claim]).model_dump())

    with (
        patch("app.agent.runner.redis_client.get_session", new=AsyncMock(return_value=None)),
        patch("app.agent.runner.redis_client.save_session", new=AsyncMock()) as mock_save,
    ):
        await _handle_result(message, "sess-1", "AAPL", citation_tracker=set(), event_queue=asyncio.Queue())

    saved_report = mock_save.call_args[0][0].partial_report
    assert saved_report.partial is True
    assert "1 claim" in saved_report.partial_reason


async def test_handle_result_grounded_claim_stays_not_partial():
    claim = Claim(text="Revenue grew", chunk_id="aaa", source_url="https://sec.gov/x", doc_name="AAPL 10-K 2024")
    message = make_result_message(structured_output=make_report(claims=[claim]).model_dump())

    with (
        patch("app.agent.runner.redis_client.get_session", new=AsyncMock(return_value=None)),
        patch("app.agent.runner.redis_client.save_session", new=AsyncMock()) as mock_save,
    ):
        await _handle_result(message, "sess-1", "AAPL", citation_tracker={"aaa"}, event_queue=asyncio.Queue())

    saved_report = mock_save.call_args[0][0].partial_report
    assert saved_report.partial is False


async def test_handle_result_error_message_sets_session_error_status():
    message = make_result_message(subtype="error_during_execution", is_error=True, result="boom")
    queue = asyncio.Queue()

    with (
        patch("app.agent.runner.redis_client.get_session", new=AsyncMock(return_value=None)),
        patch("app.agent.runner.redis_client.save_session", new=AsyncMock()) as mock_save,
    ):
        await _handle_result(message, "sess-1", "AAPL", citation_tracker=set(), event_queue=queue)

    saved_session = mock_save.call_args[0][0]
    assert saved_session.status == "error"
    assert saved_session.error_message == "boom"
    event = queue.get_nowait()
    assert isinstance(event, ErrorEvent)
    assert event.message == "boom"


# ---------------------------------------------------------------------------
# _load_or_init_session
# ---------------------------------------------------------------------------

async def test_load_or_init_session_returns_existing():
    existing = make_session()
    with patch("app.agent.runner.redis_client.get_session", new=AsyncMock(return_value=existing)):
        result = await _load_or_init_session("sess-1", "AAPL")
    assert result is existing


async def test_load_or_init_session_creates_fresh_when_missing():
    with patch("app.agent.runner.redis_client.get_session", new=AsyncMock(return_value=None)):
        result = await _load_or_init_session("sess-1", "AAPL")
    assert result.session_id == "sess-1"
    assert result.ticker == "AAPL"
    assert result.status == "running"
    assert result.partial_report is None


# ---------------------------------------------------------------------------
# answer_question
# ---------------------------------------------------------------------------

async def test_answer_question_raises_when_session_missing():
    with patch("app.agent.runner.redis_client.get_session", new=AsyncMock(return_value=None)):
        with pytest.raises(RunnerError):
            await answer_question("What's the P/E?", "AAPL", "sess-1")


async def test_answer_question_happy_path():
    session = make_session(status="done")
    answer = Answer(text="The P/E is 30.", sources=[])
    result_message = make_result_message(structured_output=answer.model_dump())

    with (
        patch("app.agent.runner.redis_client.get_session", new=AsyncMock(return_value=session)),
        patch("app.agent.runner.redis_client.append_message", new=AsyncMock()) as mock_append,
        patch("app.agent.runner.query", new=make_fake_query([result_message])),
    ):
        result = await answer_question("What's the P/E?", "AAPL", "sess-1")

    assert result.text == "The P/E is 30."
    assert mock_append.call_args_list[0].args == ("sess-1", "user", "What's the P/E?")
    assert mock_append.call_args_list[1].args == ("sess-1", "assistant", "The P/E is 30.")


async def test_answer_question_raises_when_no_result_message():
    session = make_session(status="done")

    with (
        patch("app.agent.runner.redis_client.get_session", new=AsyncMock(return_value=session)),
        patch("app.agent.runner.query", new=make_fake_query([])),
    ):
        with pytest.raises(RunnerError, match="no result message"):
            await answer_question("q", "AAPL", "sess-1")


async def test_answer_question_raises_when_result_is_error():
    session = make_session(status="done")
    result_message = make_result_message(is_error=True, result="rate limited")

    with (
        patch("app.agent.runner.redis_client.get_session", new=AsyncMock(return_value=session)),
        patch("app.agent.runner.query", new=make_fake_query([result_message])),
    ):
        with pytest.raises(RunnerError, match="rate limited"):
            await answer_question("q", "AAPL", "sess-1")
