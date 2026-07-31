"""
Unit tests for agent/prompts.py — pure string-building, no network required.
"""

from datetime import datetime

from app.agent.prompts import build_followup_prompt, build_system_prompt
from app.models.report import ResearchReport

# ---------------------------------------------------------------------------
# build_system_prompt
# ---------------------------------------------------------------------------

def test_system_prompt_contains_ticker():
    prompt = build_system_prompt("AAPL")
    assert "AAPL" in prompt


def test_system_prompt_tool_order():
    prompt = build_system_prompt("AAPL")
    tools = ["rag_retrieval_tool", "edgar_fetch_tool", "stock_data_tool", "web_search_tool", "code_execution_tool"]
    positions = [prompt.index(t) for t in tools]
    assert positions == sorted(positions)


def test_system_prompt_no_digest_without_prior_reports():
    prompt = build_system_prompt("AAPL", prior_reports=None)
    assert "Prior reports" not in prompt


def test_system_prompt_digest_lists_verdict_and_date():
    prior = [
        ResearchReport(
            ticker="AAPL",
            bull_case=[],
            bear_case=[],
            verdict="bullish",
            confidence=0.8,
            tool_trace=[],
            metrics={},
            partial=False,
            partial_reason=None,
            generated_at=datetime(2026, 1, 15),
        )
    ]
    prompt = build_system_prompt("AAPL", prior_reports=prior)
    assert "Prior reports" in prompt
    assert "2026-01-15" in prompt
    assert "verdict=bullish" in prompt
    assert "confidence=0.80" in prompt


def test_system_prompt_digest_multiple_reports():
    prior = [
        ResearchReport(
            ticker="AAPL", bull_case=[], bear_case=[], verdict="neutral", confidence=0.5,
            tool_trace=[], metrics={}, partial=False, partial_reason=None,
            generated_at=datetime(2025, 12, 1),
        ),
        ResearchReport(
            ticker="AAPL", bull_case=[], bear_case=[], verdict="bearish", confidence=0.6,
            tool_trace=[], metrics={}, partial=False, partial_reason=None,
            generated_at=datetime(2026, 1, 15),
        ),
    ]
    prompt = build_system_prompt("AAPL", prior_reports=prior)
    assert prompt.count("verdict=") == 2
    # most recent last, per docstring convention
    assert prompt.index("2025-12-01") < prompt.index("2026-01-15")


# ---------------------------------------------------------------------------
# build_followup_prompt
# ---------------------------------------------------------------------------

def test_followup_prompt_contains_question_and_ticker():
    prompt = build_followup_prompt("What's the P/E ratio?", "AAPL", [])
    assert "What's the P/E ratio?" in prompt
    assert "AAPL" in prompt


def test_followup_prompt_empty_history():
    prompt = build_followup_prompt("question", "AAPL", [])
    assert "(no prior turns)" in prompt


def test_followup_prompt_renders_history_in_order():
    messages = [
        {"role": "user", "content": "What's the revenue?"},
        {"role": "assistant", "content": "Revenue is $100B."},
    ]
    prompt = build_followup_prompt("follow up", "AAPL", messages)
    assert "(no prior turns)" not in prompt
    user_idx = prompt.index("user: What's the revenue?")
    assistant_idx = prompt.index("assistant: Revenue is $100B.")
    assert user_idx < assistant_idx
