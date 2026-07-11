"""
MCP tool: web_search_tool

Agent calls this tool for recent events and analyst commentary (earning beats, product launches,
lawsuits) that would not appear in 10-K filings
"""

from fastmcp import FastMCP
from pydantic import BaseModel

from app.clients.tavily import search, NewsResult

mcp = FastMCP("web-search")


class SearchResults(BaseModel):
    query: str
    results: list[NewsResult]


class ToolError(BaseModel):
    tool: str
    message: str


@mcp.tool()
async def web_search_tool(query: str, count: int = 5) -> SearchResults | ToolError:
    try:
        results = await search(query, count)
        return SearchResults(query=query, results=results)
    except Exception as exc:
        return ToolError(tool="web_search_tool", message=str(exc))