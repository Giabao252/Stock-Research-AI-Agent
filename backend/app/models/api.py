"""
Request/response schemas for the gateway and agent routers.
"""
from pydantic import BaseModel

from app.models.report import Claim


class AnalyzeRequest(BaseModel):
    ticker: str


class AskRequest(BaseModel):
    question: str
    ticker: str
    session_id: str


class Answer(BaseModel):
    text: str
    sources: list[Claim]
