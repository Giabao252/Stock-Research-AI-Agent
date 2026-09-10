"""
Request/response schemas for the gateway and agent routers.
The json_schema_extra examples appear pre-filled in Swagger UI at /docs.
"""
from pydantic import BaseModel, ConfigDict

from app.models.report import Claim

_EXAMPLE_SESSION_ID = "3fa85f64-5717-4562-b3fc-2c963f66afa6"


class AnalyzeRequest(BaseModel):
    model_config = ConfigDict(json_schema_extra={"example": {"ticker": "AAPL"}})
    ticker: str


class AnalyzeResponse(BaseModel):
    model_config = ConfigDict(json_schema_extra={
        "example": {"session_id": _EXAMPLE_SESSION_ID, "ticker": "AAPL"}
    })
    session_id: str
    ticker: str


class AskRequest(BaseModel):
    model_config = ConfigDict(json_schema_extra={
        "example": {
            "question": "What is AAPL's current P/E ratio and how does it compare to its 5-year average?",
            "ticker": "AAPL",
            "session_id": _EXAMPLE_SESSION_ID,
        }
    })
    question: str
    ticker: str
    session_id: str


class Answer(BaseModel):
    text: str
    sources: list[Claim]
