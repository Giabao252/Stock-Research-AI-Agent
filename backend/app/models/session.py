"""
SessionState (Redis-persisted agent run state) and the StreamEvent
discriminated union emitted over SSE while a run is in progress.
Mirrors the TypeScript StreamEvent union in CLAUDE.md field-for-field.
"""
from datetime import datetime
from typing import Literal

from pydantic import BaseModel

from app.models.report import ResearchReport


class SessionState(BaseModel):
    session_id: str
    ticker: str
    status: Literal["running", "done", "error"]
    messages: list[dict]              # conversation buffer, capped at last 8 turns for /ask
    partial_report: ResearchReport | None
    error_message: str | None
    created_at: datetime


class ThoughtEvent(BaseModel):
    type: Literal["thought"] = "thought"
    content: str


class ToolCallEvent(BaseModel):
    type: Literal["tool_call"] = "tool_call"
    tool: str
    args: dict


class ObserveEvent(BaseModel):
    type: Literal["observe"] = "observe"
    summary: str


class DoneEvent(BaseModel):
    type: Literal["done"] = "done"
    report_id: str


class ErrorEvent(BaseModel):
    type: Literal["error"] = "error"
    message: str


StreamEvent = ThoughtEvent | ToolCallEvent | ObserveEvent | DoneEvent | ErrorEvent
