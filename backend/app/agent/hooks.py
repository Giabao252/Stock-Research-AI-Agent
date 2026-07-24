"""
PreToolUse / PostToolUse hook factories for the Agent SDK.

Public API:
    make_pre_tool_use_hook()                                   -> HookCallback
    make_post_tool_use_hook(event_queue, citation_tracker)      -> HookCallback

PreToolUse blocks obviously dangerous code_execution_tool input as defense-in-depth
in front of RestrictedPython (which does the real sandboxing). PostToolUse pushes an
ObserveEvent for every tool call onto event_queue — the queue is the fan-in point
between hook callbacks (which can't be iterated like query() messages) and
agent/runner.py's generator — and records chunk_ids returned by rag_retrieval_tool
into citation_tracker so runner.py can later verify every claim in the final
ResearchReport is actually grounded in a chunk the agent saw this session.
"""

import asyncio
from typing import Any

from claude_agent_sdk import HookCallback

from app.models.session import ObserveEvent

DANGEROUS_CODE_PATTERNS = ("import os", "import sys", "subprocess", "__import__", "open(")


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


def _extract_chunk_ids(tool_response: Any) -> list[str]:
    if not isinstance(tool_response, dict):
        return []
    chunks = tool_response.get("chunks")
    if not isinstance(chunks, list):
        return []
    return [c["chunk_id"] for c in chunks if isinstance(c, dict) and "chunk_id" in c]


def _summarize(tool_name: str, tool_response: Any) -> str:
    short_name = tool_name.rsplit("__", 1)[-1]
    if isinstance(tool_response, dict) and "message" in tool_response and "tool" in tool_response:
        return f"{short_name} failed: {tool_response['message']}"

    chunk_ids = _extract_chunk_ids(tool_response)
    if chunk_ids:
        return f"{short_name} returned {len(chunk_ids)} chunk(s)"
    return f"Called {short_name}"


def make_post_tool_use_hook( event_queue: "asyncio.Queue", citation_tracker: set[str] ) -> HookCallback:
    async def hook(input_data, tool_use_id, context):
        tool_name = input_data["tool_name"]
        tool_response = input_data.get("tool_response")

        citation_tracker.update(_extract_chunk_ids(tool_response))
        await event_queue.put(ObserveEvent(summary=_summarize(tool_name, tool_response)))
        return {}

    return hook
