"""School Finance MCP server.

Exposes California SACS account-string tools and a school-meal reimbursement
calculator over the Model Context Protocol. Speaks stdio by default for local
clients, or streamable HTTP (at /mcp) for remote use.
"""

from __future__ import annotations

import argparse
import os

from mcp.server.fastmcp import FastMCP
from mcp.server.transport_security import TransportSecuritySettings

from . import cnp, sacs

# stateless_http: every tool here is a pure function, so remote HTTP mode needs
# no per-session state and stays deployable behind restarts and load balancers.
mcp = FastMCP("school-finance", stateless_http=True)


@mcp.tool()
def validate_sacs_string(account_string: str, fiscal_year: str | None = None) -> dict:
    """Validate a California SACS account string against CDE's rules.

    Accepts a delimited form ("01-0000-0-1110-1000-1100") or a packed 19-digit
    form. Checks field widths and numeric content, then CDE's valid-code lists
    (CHECKFUND, CHECKRESOURCE, CHECKGOAL, CHECKFUNCTION, CHECKOBJECT) and the
    seven valid-combination matrices (CHK-FUNDxRESOURCE, CHK-FUNDxGOAL,
    CHK-FUNDxFUNCTION-A/B, CHK-FUNDxOBJECT, CHK-FUNCTIONxOBJECT,
    CHK-GOALxFUNCTION-A/B, CHK-RESOURCExOBJECTA/B) under the same check ids the
    SACS technical review uses. Returns `valid`, structural `errors`, heuristic
    `warnings`, `components`, `normalized`, `tables` (fiscal year applied) and
    `cde_checks` (code errors, combination errors with CDE severity, passed,
    not covered, not evaluated). `fiscal_year` like "2025-26" selects that
    year's tables; default is the latest on file. Reports problems only; it does
    not propose replacement codes or check balances.
    """
    return sacs.validate(account_string, fiscal_year)


@mcp.tool()
def decode_sacs_string(account_string: str) -> dict:
    """Decode a California SACS account string into its six components.

    Returns each of fund, resource, project year, goal, function, and object
    with its code and a human-readable description (and the restriction band for
    the resource).
    """
    return sacs.decode(account_string)


@mcp.tool()
def list_sacs_codes(field: str, fiscal_year: str | None = None) -> dict:
    """List CDE's valid SACS codes for a field, with descriptive reference.

    `field` is one of: fund, resource, project_year, goal, function, object.
    For the five coded dimensions the result carries CDE's full `codes`
    list for the fiscal year (`fiscal_year` like "2025-26"; default latest).
    """
    return sacs.list_codes(field, fiscal_year)


@mcp.tool()
def calculate_meal_reimbursement(
    free_lunches: int = 0,
    reduced_lunches: int = 0,
    paid_lunches: int = 0,
    free_breakfasts: int = 0,
    reduced_breakfasts: int = 0,
    paid_breakfasts: int = 0,
    high_isp: bool = False,
    severe_need_breakfast: bool = False,
    performance_based: bool = False,
    california_universal_meals: bool = False,
) -> dict:
    """Compute federal (and optional California Universal Meals) meal reimbursement.

    Provide counts of lunches and breakfasts by category (free, reduced, paid).
    Set `high_isp=True` for the 60%-or-above lunch tier, `severe_need_breakfast=True`
    for the severe-need breakfast tier, `performance_based=True` to add 9 cents per
    lunch, and `california_universal_meals=True` to add the California state top-up.
    Returns an itemized federal and state breakdown plus the total. SY 2025-26 rates.
    """
    return cnp.calculate_meal_reimbursement(
        free_lunches=free_lunches,
        reduced_lunches=reduced_lunches,
        paid_lunches=paid_lunches,
        free_breakfasts=free_breakfasts,
        reduced_breakfasts=reduced_breakfasts,
        paid_breakfasts=paid_breakfasts,
        high_isp=high_isp,
        severe_need_breakfast=severe_need_breakfast,
        performance_based=performance_based,
        california_universal_meals=california_universal_meals,
    )


def http_transport_security(extra_hosts: list[str]) -> TransportSecuritySettings:
    """Build the Host-header allowlist for http mode.

    Localhost forms are always allowed. On Render, the public hostname arrives
    via $RENDER_EXTERNAL_HOSTNAME and is allowed automatically. Pass "*" as an
    extra host to disable DNS rebinding protection entirely (only sensible
    behind a proxy that already pins the Host header).
    """
    if "*" in extra_hosts:
        return TransportSecuritySettings(enable_dns_rebinding_protection=False)

    hosts = ["127.0.0.1:*", "localhost:*", "[::1]:*"]
    origins = ["http://127.0.0.1:*", "http://localhost:*", "http://[::1]:*"]
    render_host = os.environ.get("RENDER_EXTERNAL_HOSTNAME")
    if render_host:
        extra_hosts = [*extra_hosts, render_host]
    for host in extra_hosts:
        hosts.extend([host, f"{host}:*"])
        origins.extend([f"https://{host}", f"http://{host}"])
    return TransportSecuritySettings(allowed_hosts=hosts, allowed_origins=origins)


def main() -> None:
    """Run the MCP server over stdio (default) or streamable HTTP."""
    parser = argparse.ArgumentParser(
        prog="school-finance-mcp",
        description="California school-finance MCP server",
    )
    parser.add_argument(
        "--transport",
        choices=["stdio", "http"],
        default="stdio",
        help="stdio for local clients (default); http serves streamable HTTP at /mcp",
    )
    parser.add_argument(
        "--host",
        default="127.0.0.1",
        help="bind address for http transport (use 0.0.0.0 in a container)",
    )
    parser.add_argument(
        "--port",
        type=int,
        default=int(os.environ.get("PORT", "8000")),
        help="port for http transport (defaults to $PORT if set, else 8000)",
    )
    parser.add_argument(
        "--allowed-host",
        action="append",
        default=[],
        metavar="HOST",
        help="extra Host header value to accept in http mode (repeatable); "
        "localhost and $RENDER_EXTERNAL_HOSTNAME are always allowed; "
        "'*' disables the host check",
    )
    args = parser.parse_args()

    if args.transport == "http":
        mcp.settings.host = args.host
        mcp.settings.port = args.port
        mcp.settings.transport_security = http_transport_security(args.allowed_host)
        mcp.run(transport="streamable-http")
    else:
        mcp.run()


if __name__ == "__main__":
    main()
