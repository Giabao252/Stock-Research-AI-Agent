"""
PreToolUse / PostToolUse hook factories for the Agent SDK.

Public API:
    CitationTracker
    make_pre_tool_use_hook()                                   -> HookCallback
    make_post_tool_use_hook(event_queue, citation_tracker)      -> HookCallback

PreToolUse blocks obviously dangerous code_execution_tool input as defense-in-depth
in front of RestrictedPython (which does the real sandboxing). PostToolUse pushes an
ObserveEvent for every tool call onto event_queue — the queue is the fan-in point
between hook callbacks (which can't be iterated like query() messages) and
agent/runner.py's generator — and populates a CitationTracker so runner.py can later
verify every claim in the final ResearchReport is actually grounded in something the
agent saw this session, not merely a real-looking chunk_id reused with a swapped-in
source_url (a real failure mode observed in a live run — see runner.py's _handle_result).
"""

import asyncio
import json
from typing import Any

from claude_agent_sdk import HookCallback

from app.models.session import ObserveEvent

DANGEROUS_CODE_PATTERNS = ("import os", "import sys", "subprocess", "__import__", "open(")


class CitationTracker:
    """What tool results were actually seen this session, for the groundedness check.

    chunk_sources maps a rag_retrieval_tool chunk_id to its real source_url — catches a
    claim reusing a real chunk_id paired with a different (fabricated) source_url.
    seen_urls holds every url returned by web_search_tool — the citation identifier for
    news-derived claims, since NewsResult has no chunk_id (nothing is persisted for it;
    Claim.chunk_id is None for these, and source_url alone must match a seen url).
    """

    def __init__(self) -> None:
        self.chunk_sources: dict[str, str] = {}
        self.seen_urls: set[str] = set()


def make_pre_tool_use_hook() -> HookCallback:
    async def hook(input_data, tool_use_id, context):
        tool_name = input_data["tool_name"]
        if tool_name.endswith("code_execution_tool"):
            code = input_data["tool_input"].get("code", "")
            for pattern in DANGEROUS_CODE_PATTERNS:
                if pattern in code:
                    return {
                        "hookSpecificOutput": {
                            "hookEventName": "PreToolUse",
                            "permissionDecision": "deny",
                            "permissionDecisionReason": f"Blocked dangerous pattern in code_execution_tool: {pattern!r}",
                        }
                    }
        return {}

    return hook


def _parse_tool_response(tool_response: Any) -> dict:
    """Normalize a PostToolUse hook's tool_response into the actual tool payload.

    Confirmed empirically against a live SDK run (tool_response is typed as `Any`
    in the SDK's own type stubs — nothing documents this): for an MCP tool call,
    tool_response arrives as a JSON-encoded *string* with the real payload nested
    one level under a "result" key, e.g. '{"result": {"chunks": [...]}}'. Built-in
    tools (Bash, ToolSearch) deliver a plain dict with no such wrapping, so both
    shapes are handled here rather than assuming one.
    """
    if isinstance(tool_response, str):
        try:
            parsed = json.loads(tool_response)
        except (json.JSONDecodeError, TypeError):
            return {}
    elif isinstance(tool_response, dict):
        parsed = tool_response
    else:
        return {}

    if isinstance(parsed, dict) and isinstance(parsed.get("result"), dict):
        return parsed["result"]
    return parsed if isinstance(parsed, dict) else {}


def _extract_chunk_sources(tool_response: Any) -> dict[str, str]:
    payload = _parse_tool_response(tool_response)
    chunks = payload.get("chunks")
    if not isinstance(chunks, list):
        return {}
    return {
        c["chunk_id"]: c["source_url"]
        for c in chunks
        if isinstance(c, dict) and "chunk_id" in c and "source_url" in c
    }


def _extract_urls(tool_response: Any) -> list[str]:
    payload = _parse_tool_response(tool_response)
    results = payload.get("results")
    if not isinstance(results, list):
        return []
    return [r["url"] for r in results if isinstance(r, dict) and "url" in r]


def _summarize(tool_name: str, tool_response: Any) -> str:
    short_name = tool_name.rsplit("__", 1)[-1]
    payload = _parse_tool_response(tool_response)
    if "message" in payload and "tool" in payload:
        return f"{short_name} failed: {payload['message']}"

    chunk_sources = _extract_chunk_sources(tool_response)
    if chunk_sources:
        return f"{short_name} returned {len(chunk_sources)} chunk(s)"

    urls = _extract_urls(tool_response)
    if urls:
        return f"{short_name} returned {len(urls)} result(s)"

    return f"Called {short_name}"


def make_post_tool_use_hook(
    event_queue: "asyncio.Queue",
    citation_tracker: CitationTracker,
) -> HookCallback:
    async def hook(input_data, tool_use_id, context):
        tool_name = input_data["tool_name"]
        tool_response = input_data.get("tool_response")

        citation_tracker.chunk_sources.update(_extract_chunk_sources(tool_response))
        citation_tracker.seen_urls.update(_extract_urls(tool_response))
        await event_queue.put(ObserveEvent(summary=_summarize(tool_name, tool_response)))
        return {}

    return hook
