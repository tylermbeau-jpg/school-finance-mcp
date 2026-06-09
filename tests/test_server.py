import asyncio

from school_finance_mcp.server import mcp


def test_server_registers_expected_tools():
    tools = asyncio.run(mcp.list_tools())
    names = {t.name for t in tools}
    expected = {
        "validate_sacs_string",
        "decode_sacs_string",
        "list_sacs_codes",
        "calculate_meal_reimbursement",
    }
    assert expected <= names
    assert len(names) >= 4
