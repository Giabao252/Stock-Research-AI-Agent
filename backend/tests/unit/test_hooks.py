"""
Unit tests for agent/hooks.py — pure functions and hook factories, no network required.
"""

import asyncio
import json

import pytest

from app.agent.hooks import (
    CitationTracker,
    DANGEROUS_CODE_PATTERNS,
    _extract_chunk_sources,
    _extract_urls,
    _parse_tool_response,
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
# _parse_tool_response
#
# Regression coverage for a real bug: a live run showed every claim in a
# ResearchReport being marked ungrounded regardless of whether it was actually
# grounded, because tool_response arrives from the real SDK as a JSON-encoded
# *string* with the payload nested under a "result" key — not the plain dict
# every earlier test (and the original hooks.py implementation) assumed.
# Captured directly from a live PostToolUse hook against the real MCP server.
# ---------------------------------------------------------------------------

REAL_RAG_TOOL_RESPONSE = (
    '{"result":{"query":"revenue","ticker":"AAPL","chunks":'
    '[{"chunk_id":"d7779b26eed08cb2","text":"...","section":"Item 8","year":2025,'
    '"source_url":"https://www.sec.gov/Archives/edgar/data/320193/aapl.htm","score":0.91}]}}'
)


def test_parse_tool_response_unwraps_real_mcp_json_string_shape():
    assert _parse_tool_response(REAL_RAG_TOOL_RESPONSE) == {
        "query": "revenue",
        "ticker": "AAPL",
        "chunks": [
            {
                "chunk_id": "d7779b26eed08cb2",
                "text": "...",
                "section": "Item 8",
                "year": 2025,
                "source_url": "https://www.sec.gov/Archives/edgar/data/320193/aapl.htm",
                "score": 0.91,
            }
        ],
    }


def test_parse_tool_response_handles_plain_dict_shape_from_builtin_tools():
    # Bash/ToolSearch deliver a plain dict, no "result" wrapping or JSON string
    assert _parse_tool_response({"matches": ["x"], "query": "y"}) == {"matches": ["x"], "query": "y"}


def test_parse_tool_response_invalid_json_string_returns_empty():
    assert _parse_tool_response("not valid json") == {}


def test_parse_tool_response_none_returns_empty():
    assert _parse_tool_response(None) == {}


def test_parse_tool_response_dict_without_result_key_passes_through():
    assert _parse_tool_response({"chunks": []}) == {"chunks": []}


# ---------------------------------------------------------------------------
# _extract_chunk_sources
# ---------------------------------------------------------------------------

def test_extract_chunk_sources_happy_path():
    tool_response = {
        "chunks": [
            {"chunk_id": "aaa", "source_url": "https://sec.gov/a"},
            {"chunk_id": "bbb", "source_url": "https://sec.gov/b"},
        ]
    }
    assert _extract_chunk_sources(tool_response) == {
        "aaa": "https://sec.gov/a",
        "bbb": "https://sec.gov/b",
    }


def test_extract_chunk_sources_real_mcp_json_string_shape():
    # The actual regression: this is what a real rag_retrieval_tool call delivers
    assert _extract_chunk_sources(REAL_RAG_TOOL_RESPONSE) == {
        "d7779b26eed08cb2": "https://www.sec.gov/Archives/edgar/data/320193/aapl.htm"
    }


def test_extract_chunk_sources_not_a_dict():
    assert _extract_chunk_sources("not a dict") == {}
    assert _extract_chunk_sources(None) == {}


def test_extract_chunk_sources_chunks_not_a_list():
    assert _extract_chunk_sources({"chunks": "oops"}) == {}


def test_extract_chunk_sources_missing_key_per_entry():
    tool_response = {
        "chunks": [
            {"chunk_id": "aaa", "source_url": "https://sec.gov/a"},
            {"chunk_id": "bbb"},  # missing source_url
            {"no_id_here": True},
            "not-a-dict",
        ]
    }
    assert _extract_chunk_sources(tool_response) == {"aaa": "https://sec.gov/a"}


def test_extract_chunk_sources_shape_without_chunks_key():
    # e.g. stock_data_tool's response shape has no "chunks" key at all
    assert _extract_chunk_sources({"ticker": "AAPL", "price": 200.0}) == {}


# ---------------------------------------------------------------------------
# _extract_urls
# ---------------------------------------------------------------------------

def test_extract_urls_happy_path():
    tool_response = {"results": [{"url": "https://a.com"}, {"url": "https://b.com"}]}
    assert _extract_urls(tool_response) == ["https://a.com", "https://b.com"]


def test_extract_urls_real_mcp_json_string_shape():
    tool_response = json.dumps({"result": {"query": "news", "results": [{"url": "https://benzinga.com/x"}]}})
    assert _extract_urls(tool_response) == ["https://benzinga.com/x"]


def test_extract_urls_not_a_dict():
    assert _extract_urls("not a dict") == []
    assert _extract_urls(None) == []


def test_extract_urls_results_not_a_list():
    assert _extract_urls({"results": "oops"}) == []


def test_extract_urls_missing_key_per_entry():
    tool_response = {"results": [{"url": "https://a.com"}, {"title": "no url"}, "not-a-dict"]}
    assert _extract_urls(tool_response) == ["https://a.com"]


def test_extract_urls_shape_without_results_key():
    assert _extract_urls({"ticker": "AAPL", "price": 200.0}) == []


# ---------------------------------------------------------------------------
# _summarize
# ---------------------------------------------------------------------------

def test_summarize_tool_error_shape():
    tool_response = {"tool": "rag_retrieval_tool", "message": "boom"}
    assert _summarize("mcp__stock-research__rag_retrieval_tool", tool_response) == "rag_retrieval_tool failed: boom"


def test_summarize_tool_error_real_mcp_json_string_shape():
    # Regression: this is the shape a real stock_data_tool rate-limit failure
    # actually arrives as — a live run showed "Called stock_data_tool" instead
    # of the failure message because the old code only checked plain dicts.
    tool_response = json.dumps({"result": {"tool": "stock-data-tool", "message": "rate limited"}})
    assert _summarize("mcp__stock-research__stock_data_tool", tool_response) == "stock_data_tool failed: rate limited"


def test_summarize_with_chunks():
    tool_response = {"chunks": [{"chunk_id": "aaa", "source_url": "https://sec.gov/a"}, {"chunk_id": "bbb", "source_url": "https://sec.gov/b"}]}
    assert _summarize("mcp__stock-research__rag_retrieval_tool", tool_response) == "rag_retrieval_tool returned 2 chunk(s)"


def test_summarize_with_urls():
    tool_response = {"results": [{"url": "https://a.com"}]}
    assert _summarize("mcp__stock-research__web_search_tool", tool_response) == "web_search_tool returned 1 result(s)"


def test_summarize_generic_tool_response():
    assert _summarize("mcp__stock-research__stock_data_tool", {"ticker": "AAPL"}) == "Called stock_data_tool"


# ---------------------------------------------------------------------------
# make_post_tool_use_hook
# ---------------------------------------------------------------------------

async def test_post_tool_use_pushes_observe_event():
    queue: asyncio.Queue = asyncio.Queue()
    tracker = CitationTracker()
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


async def test_post_tool_use_populates_chunk_sources_for_rag_shape():
    queue: asyncio.Queue = asyncio.Queue()
    tracker = CitationTracker()
    hook = make_post_tool_use_hook(queue, tracker)

    await hook(
        {
            "tool_name": "mcp__stock-research__rag_retrieval_tool",
            "tool_response": {
                "chunks": [
                    {"chunk_id": "aaa", "source_url": "https://sec.gov/a"},
                    {"chunk_id": "bbb", "source_url": "https://sec.gov/b"},
                ]
            },
        },
        "tool-use-1",
        None,
    )

    assert tracker.chunk_sources == {"aaa": "https://sec.gov/a", "bbb": "https://sec.gov/b"}
    assert tracker.seen_urls == set()


async def test_post_tool_use_populates_seen_urls_for_web_search_shape():
    queue: asyncio.Queue = asyncio.Queue()
    tracker = CitationTracker()
    hook = make_post_tool_use_hook(queue, tracker)

    await hook(
        {
            "tool_name": "mcp__stock-research__web_search_tool",
            "tool_response": {"results": [{"url": "https://benzinga.com/x"}]},
        },
        "tool-use-1",
        None,
    )

    assert tracker.seen_urls == {"https://benzinga.com/x"}
    assert tracker.chunk_sources == {}


async def test_post_tool_use_populates_chunk_sources_from_real_mcp_json_string_shape():
    # End-to-end regression for the live-run bug: tool_response as the real SDK
    # actually delivers it (JSON string, "result"-wrapped), through the actual
    # hook — not just the extraction helpers in isolation.
    queue: asyncio.Queue = asyncio.Queue()
    tracker = CitationTracker()
    hook = make_post_tool_use_hook(queue, tracker)

    await hook(
        {
            "tool_name": "mcp__stock-research__rag_retrieval_tool",
            "tool_response": REAL_RAG_TOOL_RESPONSE,
        },
        "tool-use-1",
        None,
    )

    assert tracker.chunk_sources == {
        "d7779b26eed08cb2": "https://www.sec.gov/Archives/edgar/data/320193/aapl.htm"
    }


async def test_post_tool_use_leaves_tracker_untouched_for_non_chunk_shape():
    queue: asyncio.Queue = asyncio.Queue()
    tracker = CitationTracker()
    tracker.chunk_sources["pre-existing"] = "https://sec.gov/pre"

    hook = make_post_tool_use_hook(queue, tracker)

    await hook(
        {
            "tool_name": "mcp__stock-research__stock_data_tool",
            "tool_response": {"ticker": "AAPL", "price": 200.0},
        },
        "tool-use-1",
        None,
    )

    assert tracker.chunk_sources == {"pre-existing": "https://sec.gov/pre"}
    assert tracker.seen_urls == set()
