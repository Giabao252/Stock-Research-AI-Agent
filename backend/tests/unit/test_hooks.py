"""
Unit tests for agent/hooks.py — pure functions and hook factories, no network required.
"""

import asyncio

import pytest

from app.agent.hooks import (
    DANGEROUS_CODE_PATTERNS,
    _extract_chunk_ids,
    _summarize,
    make_post_tool_use_hook,
    make_pre_tool_use_hook,
)
from app.models.session import ObserveEvent

# ---------------------------------------------------------------------------
# make_pre_tool_use_hook
# ---------------------------------------------------------------------------

async def test_pre_tool_use_allows_non_code_execution_tool():
    hook = make_pre_tool_use_hook()
    result = await hook(
        {"tool_name": "mcp__stock-research__stock_data_tool", "tool_input": {}},
        "tool-use-1",
        None,
    )
    assert result == {}


async def test_pre_tool_use_allows_clean_code():
    hook = make_pre_tool_use_hook()
    result = await hook(
        {
            "tool_name": "mcp__stock-research__code_execution_tool",
            "tool_input": {"code": "result = 1 + 1"},
        },
        "tool-use-1",
        None,
    )
    assert result == {}


@pytest.mark.parametrize("pattern", DANGEROUS_CODE_PATTERNS)
async def test_pre_tool_use_denies_dangerous_patterns(pattern):
    hook = make_pre_tool_use_hook()
    code = f"{pattern}os.system('rm -rf /')" if pattern != "open(" else "open('/etc/passwd')"
    result = await hook(
        {
            "tool_name": "mcp__stock-research__code_execution_tool",
            "tool_input": {"code": code},
        },
        "tool-use-1",
        None,
    )
    output = result["hookSpecificOutput"]
    assert output["hookEventName"] == "PreToolUse"
    assert output["permissionDecision"] == "deny"
    assert pattern in output["permissionDecisionReason"]


# ---------------------------------------------------------------------------
# _extract_chunk_ids
# ---------------------------------------------------------------------------

def test_extract_chunk_ids_happy_path():
    tool_response = {"chunks": [{"chunk_id": "aaa"}, {"chunk_id": "bbb"}]}
    assert _extract_chunk_ids(tool_response) == ["aaa", "bbb"]


def test_extract_chunk_ids_not_a_dict():
    assert _extract_chunk_ids("not a dict") == []
    assert _extract_chunk_ids(None) == []


def test_extract_chunk_ids_chunks_not_a_list():
    assert _extract_chunk_ids({"chunks": "oops"}) == []


def test_extract_chunk_ids_missing_key_per_entry():
    tool_response = {"chunks": [{"chunk_id": "aaa"}, {"no_id_here": True}, "not-a-dict"]}
    assert _extract_chunk_ids(tool_response) == ["aaa"]


def test_extract_chunk_ids_shape_without_chunks_key():
    # e.g. stock_data_tool's response shape has no "chunks" key at all
    assert _extract_chunk_ids({"ticker": "AAPL", "price": 200.0}) == []


# ---------------------------------------------------------------------------
# _summarize
# ---------------------------------------------------------------------------

def test_summarize_tool_error_shape():
    tool_response = {"tool": "rag_retrieval_tool", "message": "boom"}
    assert _summarize("mcp__stock-research__rag_retrieval_tool", tool_response) == "rag_retrieval_tool failed: boom"


def test_summarize_with_chunks():
    tool_response = {"chunks": [{"chunk_id": "aaa"}, {"chunk_id": "bbb"}]}
    assert _summarize("mcp__stock-research__rag_retrieval_tool", tool_response) == "rag_retrieval_tool returned 2 chunk(s)"


def test_summarize_generic_tool_response():
    assert _summarize("mcp__stock-research__stock_data_tool", {"ticker": "AAPL"}) == "Called stock_data_tool"


# ---------------------------------------------------------------------------
# make_post_tool_use_hook
# ---------------------------------------------------------------------------

async def test_post_tool_use_pushes_observe_event():
    queue: asyncio.Queue = asyncio.Queue()
    tracker: set[str] = set()
    hook = make_post_tool_use_hook(queue, tracker)

    result = await hook(
        {
            "tool_name": "mcp__stock-research__stock_data_tool",
            "tool_response": {"ticker": "AAPL"},
        },
        "tool-use-1",
        None,
    )

    assert result == {}
    event = queue.get_nowait()
    assert isinstance(event, ObserveEvent)
    assert event.summary == "Called stock_data_tool"


async def test_post_tool_use_populates_citation_tracker_for_rag_shape():
    queue: asyncio.Queue = asyncio.Queue()
    tracker: set[str] = set()
    hook = make_post_tool_use_hook(queue, tracker)

    await hook(
        {
            "tool_name": "mcp__stock-research__rag_retrieval_tool",
            "tool_response": {"chunks": [{"chunk_id": "aaa"}, {"chunk_id": "bbb"}]},
        },
        "tool-use-1",
        None,
    )

    assert tracker == {"aaa", "bbb"}


async def test_post_tool_use_leaves_tracker_untouched_for_non_chunk_shape():
    queue: asyncio.Queue = asyncio.Queue()
    tracker: set[str] = {"pre-existing"}
    hook = make_post_tool_use_hook(queue, tracker)

    await hook(
        {
            "tool_name": "mcp__stock-research__stock_data_tool",
            "tool_response": {"ticker": "AAPL", "price": 200.0},
        },
        "tool-use-1",
        None,
    )

    assert tracker == {"pre-existing"}
