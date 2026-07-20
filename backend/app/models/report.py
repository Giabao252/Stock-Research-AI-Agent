import datetime
from typing import Literal
from pydantic import BaseModel

class ToolCall(BaseModel):
    tool: str
    args: dict
    result_summary: str

class Claim(BaseModel):
    text: str
    chunk_id: str
    source_url: str
    doc_name: str

class ResearchReport(BaseModel):
    ticker: str
    bull_case: list[Claim]
    bear_case: list[Claim]
    verdict: Literal['bullish', 'bearish', 'neutral']
    confidence: float
    tool_trace: list[ToolCall]
    metrics: dict
    partial: bool
    partial_reason: str | None
    generated_at: datetime