"""End-to-end test of the streamable HTTP transport.

Spawns the server as a real subprocess on a free port, then drives it with the
official MCP streamable HTTP client: initialize, list tools, and call two tools.
"""

from __future__ import annotations

import json
import socket
import subprocess
import sys
import time

import anyio
from mcp import ClientSession

try:
    from mcp.client.streamable_http import streamable_http_client
except ImportError:  # SDK versions before the rename
    from mcp.client.streamable_http import (
        streamablehttp_client as streamable_http_client,
    )

EXPECTED_TOOLS = {
    "validate_sacs_string",
    "decode_sacs_string",
    "list_sacs_codes",
    "calculate_meal_reimbursement",
}


def _free_port() -> int:
    with socket.socket() as s:
        s.bind(("127.0.0.1", 0))
        return s.getsockname()[1]


def _wait_for_port(port: int, proc: subprocess.Popen, timeout: float = 20.0) -> None:
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        if proc.poll() is not None:
            raise RuntimeError(f"server exited early with code {proc.returncode}")
        try:
            with socket.create_connection(("127.0.0.1", port), timeout=0.5):
                return
        except OSError:
            time.sleep(0.2)
    raise TimeoutError(f"server did not listen on port {port} within {timeout}s")


def _payload(result) -> dict:
    # Tools return plain dicts, which the server serializes as JSON text content.
    assert not result.isError
    return json.loads(result.content[0].text)


async def _exercise(url: str) -> None:
    async with streamable_http_client(url) as (read, write, _):
        async with ClientSession(read, write) as session:
            await session.initialize()

            tools = await session.list_tools()
            assert {t.name for t in tools.tools} == EXPECTED_TOOLS

            result = await session.call_tool(
                "validate_sacs_string",
                {"account_string": "01-0000-0-1110-1000-1100"},
            )
            assert _payload(result)["valid"] is True

            result = await session.call_tool(
                "calculate_meal_reimbursement",
                {"free_lunches": 100, "california_universal_meals": True},
            )
            assert _payload(result)["total_reimbursement"] > 0


def test_http_transport_end_to_end():
    port = _free_port()
    proc = subprocess.Popen(
        [
            sys.executable,
            "-m",
            "school_finance_mcp",
            "--transport",
            "http",
            "--port",
            str(port),
        ],
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )
    try:
        _wait_for_port(port, proc)
        anyio.run(_exercise, f"http://127.0.0.1:{port}/mcp")
    finally:
        proc.terminate()
        proc.wait(timeout=10)
