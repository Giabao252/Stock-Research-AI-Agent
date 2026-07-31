from fastmcp import FastMCP
from app.mcp_servers import rag_tool, edgar_tool, stock_tool, search_tool, code_tool

mcp = FastMCP("stock-research")

mcp.mount(rag_tool.mcp)
mcp.mount(edgar_tool.mcp)
mcp.mount(stock_tool.mcp)
mcp.mount(search_tool.mcp)
mcp.mount(code_tool.mcp)

# Run via the fastmcp CLI, not this file directly — it ignores __main__ blocks:
#   fastmcp run app/mcp_servers/server.py --transport http --port 8001