"""
Unit tests for mcp_servers/rag_tool.py — the underlying async function is
called directly (the @mcp.tool() decorator doesn't replace it in the module
namespace). retrieve() is mocked; MCP protocol wiring itself is covered
separately in tests/integration/test_mcp_wiring.py.
"""

from unittest.mock import AsyncMock, patch

from app.mcp_servers.rag_tool import ToolError, rag_retrieval_tool
from app.models.chunk import Chunk


def make_chunk(chunk_id="aaa", score=0.9) -> Chunk:
    return Chunk(
        chunk_id=chunk_id,
        text="Apple faces competition risk",
        ticker="AAPL",
        section="Item 1A",
        year=2024,
        source_url="https://sec.gov/test",
        score=score,
    )


async def test_rag_retrieval_tool_maps_chunks_field_by_field():
    chunk = make_chunk()
    with patch("app.mcp_servers.rag_tool.retrieve", new=AsyncMock(return_value=[chunk])):
        result = await rag_retrieval_tool(query="risk", ticker="AAPL")

    assert result.query == "risk"
    assert result.ticker == "AAPL"
    assert len(result.chunks) == 1
    summary = result.chunks[0]
    assert summary.chunk_id == chunk.chunk_id
    assert summary.text == chunk.text
    assert summary.section == chunk.section
    assert summary.year == chunk.year
    assert summary.source_url == chunk.source_url
    assert summary.score == chunk.score


async def test_rag_retrieval_tool_empty_results():
    with patch("app.mcp_servers.rag_tool.retrieve", new=AsyncMock(return_value=[])):
        result = await rag_retrieval_tool(query="risk", ticker="ZZZZ")

    assert result.chunks == []


async def test_rag_retrieval_tool_passes_through_args():
    with patch("app.mcp_servers.rag_tool.retrieve", new=AsyncMock(return_value=[])) as mock_retrieve:
        await rag_retrieval_tool(query="risk", ticker="AAPL", top_k=3, section="Item 1A")

    mock_retrieve.assert_awaited_once_with(query="risk", ticker="AAPL", top_k=3, section="Item 1A")


async def test_rag_retrieval_tool_returns_tool_error_on_exception():
    with patch("app.mcp_servers.rag_tool.retrieve", new=AsyncMock(side_effect=RuntimeError("qdrant down"))):
        result = await rag_retrieval_tool(query="risk", ticker="AAPL")

    assert isinstance(result, ToolError)
    assert result.tool == "rag_retrieval_tool"
    assert "qdrant down" in result.message
