"""
MCP tool: edgar_fetch_tool

Called by the agent when the RAG retrieval returns zero chunks -> the ticker hasn't been 
ingested yet -> calls edgar_fetch_tool to pull the 10-K filings from SEC, run the ingestion 
pipeline again, load to Qdrant again.
"""

from fastmcp import FastMCP
from pydantic import BaseModel

from app.rag.ingest import ingest_ticker

mcp = FastMCP("edgar-fetch")

class IngestResult(BaseModel):
    ticker: str
    chunks_upserted: int
    status: str #success || "no filings found"

class ToolError(BaseModel):
    tool: str
    message: str

@mcp.tool()
async def edgar_fetch_tool(ticker: str) -> IngestResult | ToolError:
    try:
        chunks_upserted = await ingest_ticker(ticker)

        if chunks_upserted == 0:
            return IngestResult(ticker=ticker, chunks_upserted=0, status="no_filings_found")
        else:
            return IngestResult(ticker=ticker, chunks_upserted=chunks_upserted, status="success")
            #agent reads this, confirms success, retries rag_retrieval_tool
    
    except Exception as exc:
        return ToolError(tool="edgar_fetch_tool", message=str(exc))
        #handles exceptions: ticker not found, embeddings error, Qdrant upsert failure    