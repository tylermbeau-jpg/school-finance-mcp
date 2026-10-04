"""End-to-end tests of http mode.

Each test spawns the server as a real subprocess on a free port. One drives it
with the official MCP streamable HTTP client (initialize, list tools, call two
tools); the others hit it the way a browser page would: the /health probe, a
CORS preflight, and a direct tools/call from allowed and refused origins.
"""

from __future__ import annotations

import contextlib
import json
import os
import socket
import subprocess
import sys
import time
import urllib.error
import urllib.request

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


@contextlib.contextmanager
def _server(*extra_args: str, env: dict | None = None):
    """Run the server in http mode on a free port and yield its base URL."""
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
            *extra_args,
        ],
        env={**os.environ, **(env or {})},
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )
    try:
        _wait_for_port(port, proc)
        yield f"http://127.0.0.1:{port}"
    finally:
        proc.terminate()
        proc.wait(timeout=10)


def test_http_transport_end_to_end():
    with _server() as base:
        anyio.run(_exercise, f"{base}/mcp")


DEMO_ORIGIN = "https://demo.example"

_CALL = json.dumps(
    {
        "jsonrpc": "2.0",
        "id": 1,
        "method": "tools/call",
        "params": {
            "name": "validate_sacs_string",
            "arguments": {"account_string": "01-0000-0-1110-1000-1100"},
        },
    }
).encode()


def _request(url: str, method: str = "GET", headers: dict | None = None, body: bytes | None = None):
    req = urllib.request.Request(url, data=body, method=method, headers=headers or {})
    try:
        with urllib.request.urlopen(req, timeout=10) as resp:
            return resp.status, resp.headers, resp.read().decode()
    except urllib.error.HTTPError as exc:
        return exc.code, exc.headers, exc.read().decode()


def _browser_call(base: str, origin: str):
    return _request(
        f"{base}/mcp",
        method="POST",
        headers={
            "Origin": origin,
            "Content-Type": "application/json",
            "Accept": "application/json, text/event-stream",
        },
        body=_CALL,
    )


def test_health_is_readable_from_any_origin():
    with _server() as base:
        status, headers, body = _request(
            f"{base}/health", headers={"Origin": "https://anywhere.example"}
        )
    assert status == 200
    assert json.loads(body) == {"status": "ok"}
    assert headers["access-control-allow-origin"] == "*"


def test_browser_call_from_allowed_origin():
    with _server("--cors-origin", DEMO_ORIGIN) as base:
        status, headers, _ = _request(
            f"{base}/mcp",
            method="OPTIONS",
            headers={
                "Origin": DEMO_ORIGIN,
                "Access-Control-Request-Method": "POST",
                "Access-Control-Request-Headers": "content-type",
            },
        )
        assert status == 200
        assert headers["access-control-allow-origin"] == DEMO_ORIGIN

        status, headers, body = _browser_call(base, DEMO_ORIGIN)
    assert status == 200
    assert headers["access-control-allow-origin"] == DEMO_ORIGIN
    # Stateless http answers a lone tools/call as one server-sent event.
    data = next(line for line in body.splitlines() if line.startswith("data: "))
    result = json.loads(data[len("data: "):])["result"]
    assert json.loads(result["content"][0]["text"])["valid"] is True


def test_browser_call_from_repo_owner_pages_origin_on_render():
    with _server(env={"RENDER_GIT_REPO_SLUG": "demo-owner/some-repo"}) as base:
        status, headers, _ = _browser_call(base, "https://demo-owner.github.io")
    assert status == 200
    assert headers["access-control-allow-origin"] == "https://demo-owner.github.io"


def test_browser_call_from_other_origin_is_refused():
    with _server("--cors-origin", DEMO_ORIGIN) as base:
        status, headers, _ = _browser_call(base, "https://other.example")
    assert status == 403
    assert headers.get("access-control-allow-origin") is None
