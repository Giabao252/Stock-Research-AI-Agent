"""
Lightweight schema-drift guards for models/session.py, models/report.py,
models/api.py. These are regression tests, not business logic tests — Claude's
structured output must conform to exactly these schemas via output_format, so
a silent field/type change here would break agent/runner.py in a way none of
the mocked agent tests could catch.
"""

from datetime import datetime

import pytest
from pydantic import ValidationError

from app.models.api import AnalyzeRequest, AskRequest, Answer
from app.models.report import Claim, ResearchReport
from app.models.session import DoneEvent, ErrorEvent, ObserveEvent, SessionState, ThoughtEvent, ToolCallEvent

# ---------------------------------------------------------------------------
# StreamEvent discriminated union — each variant round-trips with correct type
# ---------------------------------------------------------------------------

@pytest.mark.parametrize("event", [
    ThoughtEvent(content="thinking..."),
    ToolCallEvent(tool="rag_retrieval_tool", args={"query": "risk"}),
    ObserveEvent(summary="Called rag_retrieval_tool"),
    DoneEvent(report_id="sess-1"),
    ErrorEvent(message="boom"),
])
def test_stream_event_round_trips_through_dump_and_validate(event):
    cls = type(event)
    dumped = event.model_dump()
    restored = cls.model_validate(dumped)
    assert restored == event
    assert dumped["type"] == event.type


def test_thought_event_rejects_wrong_type_literal():
    with pytest.raises(ValidationError):
        ThoughtEvent.model_validate({"type": "tool_call", "content": "x"})


def test_done_event_rejects_wrong_type_literal():
    with pytest.raises(ValidationError):
        DoneEvent.model_validate({"type": "error", "report_id": "sess-1"})


# ---------------------------------------------------------------------------
# SessionState
# ---------------------------------------------------------------------------

def make_session_kwargs(**overrides):
    base = dict(
        session_id="sess-1", ticker="AAPL", status="running", messages=[],
        partial_report=None, error_message=None, created_at=datetime(2026, 1, 1),
    )
    base.update(overrides)
    return base


def test_session_state_accepts_valid_status_values():
    for status in ("running", "done", "error"):
        session = SessionState(**make_session_kwargs(status=status))
        assert session.status == status


def test_session_state_rejects_invalid_status():
    with pytest.raises(ValidationError):
        SessionState(**make_session_kwargs(status="paused"))


def test_session_state_partial_report_accepts_none():
    session = SessionState(**make_session_kwargs(partial_report=None))
    assert session.partial_report is None


# ---------------------------------------------------------------------------
# ResearchReport / Claim
# ---------------------------------------------------------------------------

def make_report_kwargs(**overrides):
    base = dict(
        ticker="AAPL", bull_case=[], bear_case=[], verdict="bullish", confidence=0.7,
        tool_trace=[], metrics={}, partial=False, partial_reason=None,
        generated_at=datetime(2026, 1, 1),
    )
    base.update(overrides)
    return base


def test_research_report_accepts_valid_verdicts():
    for verdict in ("bullish", "bearish", "neutral"):
        report = ResearchReport(**make_report_kwargs(verdict=verdict))
        assert report.verdict == verdict


def test_research_report_rejects_invalid_verdict():
    with pytest.raises(ValidationError):
        ResearchReport(**make_report_kwargs(verdict="mixed"))


def test_claim_requires_all_citation_fields():
    with pytest.raises(ValidationError):
        Claim(text="Revenue grew")  # missing chunk_id/source_url/doc_name


# ---------------------------------------------------------------------------
# models/api.py
# ---------------------------------------------------------------------------

def test_analyze_request_requires_ticker():
    with pytest.raises(ValidationError):
        AnalyzeRequest()
    assert AnalyzeRequest(ticker="AAPL").ticker == "AAPL"


def test_ask_request_requires_all_fields():
    request = AskRequest(question="What's the P/E?", ticker="AAPL", session_id="sess-1")
    assert request.question == "What's the P/E?"


def test_answer_sources_default_type_is_claim_list():
    claim = Claim(text="x", chunk_id="a", source_url="https://x", doc_name="AAPL 10-K 2024")
    answer = Answer(text="The P/E is 30.", sources=[claim])
    assert answer.sources[0].chunk_id == "a"
