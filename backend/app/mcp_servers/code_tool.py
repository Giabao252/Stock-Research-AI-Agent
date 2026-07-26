"""
MCP Tool: code_execution_tool

Lets the agent run small financial math snippets safely using RestrictedPython.
The agent must assign its computed value to a variable named `result`.
No imports, file I/O, or network access are permitted inside the snippet.
"""

from RestrictedPython import compile_restricted, safe_globals
from RestrictedPython import PrintCollector
from RestrictedPython.Eval import default_guarded_getitem
from fastmcp import FastMCP
from pydantic import BaseModel

mcp = FastMCP("code-execution")


class ExecutionResult(BaseModel):
    result: float | int | str | None
    stdout_output: str
    error: str | None


@mcp.tool()
async def code_execution_tool(code: str, context: dict) -> ExecutionResult:
    """Execute a short Python snippet with access to `context` (a dict of financial values).

    The snippet must assign its final value to a variable named `result`.
    Example:
        code:    "result = context['pe_ratio'] / (context['growth_rate'] * 100)"
        context: {"pe_ratio": 35.2, "growth_rate": 0.18}

    No imports, file I/O, or network calls allowed.
    Returns the value of `result` and any printed output.
    If a compile or runtime error occurs, result is None and error contains the message.
    """
    try:
        compiled = compile_restricted(code, "<string>", "exec")
    except SyntaxError as exc:
        return ExecutionResult(result=None, stdout_output="", error=f"SyntaxError: {exc}")

    glb = {
        **safe_globals,
        "_print_": PrintCollector,
        "_getiter_": iter,
        "_getattr_": getattr,
        "_getitem_": default_guarded_getitem,
        "context": context,
    }

    try:
        exec(compiled, glb)  # noqa: S102
    except Exception as exc:
        return ExecutionResult(result=None, stdout_output="", error=str(exc))

    result = glb.get("result")
    stdout_output = glb.get("_print", lambda: "")()

    return ExecutionResult(result=result, stdout_output=stdout_output, error=None)
