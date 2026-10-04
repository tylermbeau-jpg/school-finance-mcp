"""School Finance MCP server.

Exposes California SACS account-string tools and a school-meal reimbursement
calculator over the Model Context Protocol. Speaks stdio by default for local
clients, or streamable HTTP (at /mcp, with a liveness probe at /health) for
remote use.
"""

from __future__ import annotations

import argparse
import os

from mcp.server.fastmcp import FastMCP
from mcp.server.transport_security import TransportSecuritySettings
from starlette.applications import Starlette
from starlette.middleware.cors import CORSMiddleware
from starlette.requests import Request
from starlette.responses import JSONResponse

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


@mcp.custom_route("/health", methods=["GET"])
async def health(request: Request) -> JSONResponse:
    """Liveness probe for http mode.

    Readable from any origin, so a status page can tell a host that is still
    waking from a server that is up. Reports nothing but the fact it answered.
    """
    return JSONResponse(
        {"status": "ok"},
        headers={"Access-Control-Allow-Origin": "*", "Cache-Control": "no-store"},
    )


def http_transport_security(
    extra_hosts: list[str], cors_origins: list[str] | None = None
) -> TransportSecuritySettings:
    """Build the Host and Origin allowlists for http mode.

    Localhost forms are always allowed. On Render, the public hostname arrives
    via $RENDER_EXTERNAL_HOSTNAME and is allowed automatically. `cors_origins`
    are extra browser origins allowed to call the server. Pass "*" as an extra
    host to disable DNS rebinding protection entirely (only sensible behind a
    proxy that already pins the Host header).
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
    origins.extend(cors_origins or [])
    return TransportSecuritySettings(allowed_hosts=hosts, allowed_origins=origins)


def browser_origins(cors_origins: list[str]) -> list[str]:
    """Browser origins allowed to call /mcp in http mode.

    These are the --cors-origin values. On Render, the GitHub Pages origin of
    the deployed repo's owner (from $RENDER_GIT_REPO_SLUG, "owner/repo") is
    added automatically, so a demo page published from the same repo works with
    no extra configuration.
    """
    origins = [origin.rstrip("/") for origin in cors_origins]
    slug = os.environ.get("RENDER_GIT_REPO_SLUG", "")
    owner = slug.split("/")[0].strip().lower() if "/" in slug else ""
    if owner and f"https://{owner}.github.io" not in origins:
        origins.append(f"https://{owner}.github.io")
    return origins


def build_http_app(extra_hosts: list[str], cors_origins: list[str]) -> Starlette:
    """Build the ASGI app for http mode: MCP at /mcp, liveness at /health.

    `cors_origins` are browser origins allowed to call /mcp directly (a demo
    page, for example). Each one joins the Origin allowlist and gets CORS
    headers. With none, pages on other origins stay blocked.
    """
    mcp.settings.transport_security = http_transport_security(extra_hosts, cors_origins)
    app = mcp.streamable_http_app()
    if cors_origins:
        app.add_middleware(
            CORSMiddleware,
            allow_origins=cors_origins,
            allow_methods=["GET", "POST", "OPTIONS"],
            allow_headers=["accept", "content-type", "mcp-protocol-version", "mcp-session-id"],
            expose_headers=["mcp-session-id"],
            max_age=86400,
        )
    return app


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
        help="stdio for local clients (default); http serves streamable HTTP at /mcp "
        "and a liveness probe at /health",
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
    parser.add_argument(
        "--cors-origin",
        action="append",
        default=[],
        metavar="ORIGIN",
        help="browser origin allowed to call /mcp in http mode (repeatable), "
        "for example https://you.github.io; on Render the repo owner's GitHub "
        "Pages origin is allowed automatically",
    )
    args = parser.parse_args()

    if args.transport == "http":
        import uvicorn

        mcp.settings.host = args.host
        mcp.settings.port = args.port
        app = build_http_app(args.allowed_host, browser_origins(args.cors_origin))
        uvicorn.run(
            app,
            host=args.host,
            port=args.port,
            log_level=mcp.settings.log_level.lower(),
        )
    else:
        mcp.run()


if __name__ == "__main__":
    main()
