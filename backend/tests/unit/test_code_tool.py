"""
Unit tests for mcp_servers/code_tool.py — pure RestrictedPython, no mocking.

Also regression-covers the PrintCollector bug fixed in this same session:
code_tool.py used to read glb["_print_"].txt (the class, and its raw list
buffer) instead of calling the actual bound "_print" instance — which made
stdout_output fail Pydantic validation (list instead of str) on every call,
including calls with no print() at all.
"""

from app.mcp_servers.code_tool import code_execution_tool


async def test_code_execution_tool_valid_arithmetic():
    result = await code_execution_tool(code="result = context['pe_ratio'] / context['growth_rate']", context={"pe_ratio": 30.0, "growth_rate": 2.0})

    assert result.result == 15.0
    assert result.error is None
    assert result.stdout_output == ""


async def test_code_execution_tool_no_result_variable():
    result = await code_execution_tool(code="x = 1 + 1", context={})

    assert result.result is None
    assert result.error is None


async def test_code_execution_tool_captures_print_output():
    result = await code_execution_tool(code="print('computing...'); result = 42", context={})

    assert result.result == 42
    assert result.error is None
    assert "computing..." in result.stdout_output


async def test_code_execution_tool_disallowed_import_blocked():
    result = await code_execution_tool(code="import os\nresult = os.getcwd()", context={})

    assert result.result is None
    assert result.error is not None


async def test_code_execution_tool_syntax_error():
    result = await code_execution_tool(code="result = (", context={})

    assert result.result is None
    assert result.error is not None
    assert result.error.startswith("SyntaxError:")


async def test_code_execution_tool_runtime_exception():
    result = await code_execution_tool(code="result = 1 / 0", context={})

    assert result.result is None
    assert result.error is not None
    assert "division" in result.error.lower() or "zero" in result.error.lower()
