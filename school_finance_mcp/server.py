"""School Finance MCP server.

Exposes California SACS account-string tools and a school-meal reimbursement
calculator over the Model Context Protocol (stdio transport).
"""

from __future__ import annotations

from mcp.server.fastmcp import FastMCP

from . import cnp, sacs

mcp = FastMCP("school-finance")


@mcp.tool()
def validate_sacs_string(account_string: str) -> dict:
    """Validate a California SACS account string.

    Accepts a delimited form ("01-0000-0-1110-1000-1100") or a packed 19-digit
    form. Checks field widths, numeric content, and known codes. Returns
    `valid`, structural `errors`, `warnings` for unrecognized codes, the parsed
    `components`, and a `normalized` form. Structural and known-code checks only;
    full valid-combination validation requires the CDE tables.
    """
    return sacs.validate(account_string)


@mcp.tool()
def decode_sacs_string(account_string: str) -> dict:
    """Decode a California SACS account string into its six components.

    Returns each of fund, resource, project year, goal, function, and object
    with its code and a human-readable description (and the restriction band for
    the resource).
    """
    return sacs.decode(account_string)


@mcp.tool()
def list_sacs_codes(field: str) -> dict:
    """List known SACS codes for a field.

    `field` is one of: fund, resource, project_year, goal, function, object.
    """
    return sacs.list_codes(field)


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


def main() -> None:
    """Run the MCP server over stdio."""
    mcp.run()


if __name__ == "__main__":
    main()
