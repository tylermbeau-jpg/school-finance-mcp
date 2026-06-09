"""California SACS (Standardized Account Code Structure) reference and validation.

Implements the CDE 19-digit state account-string structure (Fund, Resource,
Project Year, Goal, Function, Object) plus a structural and known-code validator
and decoder. This is built from the public CDE SACS specification, not from any
district's internal chart of accounts.

Scope and honesty: the validator checks field structure (widths, numeric, total
length) and looks up known codes and ranges. It does NOT perform the full
valid-combination check that the CDE enforces (which Resource/Goal/Function/
Object combinations are allowed together, by entity type). For official
validation, use the CDE's downloadable valid-code and valid-combination tables,
refreshed each fiscal year. See README for sources.
"""

from __future__ import annotations

import re

# Field order and widths per the CDE SACS Import File Specifications.
FIELDS = [
    ("fund", 2),
    ("resource", 4),
    ("project_year", 1),
    ("goal", 4),
    ("function", 4),
    ("object", 4),
]
TOTAL_WIDTH = sum(width for _, width in FIELDS)  # 19

# Common Fund codes. Not exhaustive: the CDE publishes the full list.
FUNDS = {
    "01": "General Fund",
    "09": "Charter Schools Special Revenue Fund",
    "10": "Special Education Pass-Through Fund",
    "11": "Adult Education Fund",
    "12": "Child Development Fund",
    "13": "Cafeteria Special Revenue Fund",
    "14": "Deferred Maintenance Fund",
    "20": "Special Reserve Fund for Postemployment Benefits",
    "21": "Building Fund",
    "25": "Capital Facilities Fund",
    "35": "County School Facilities Fund",
    "40": "Special Reserve Fund for Capital Outlay Projects",
    "51": "Bond Interest and Redemption Fund",
    "61": "Cafeteria Enterprise Fund",
    "62": "Charter Schools Enterprise Fund",
}

# Object code series, keyed by leading digit.
OBJECT_SERIES = {
    "1": "Certificated Salaries",
    "2": "Classified Salaries",
    "3": "Employee Benefits",
    "4": "Books and Supplies",
    "5": "Services and Other Operating Expenditures",
    "6": "Capital Outlay",
    "7": "Other Outgo",
    "8": "Revenues",
    "9": "Balance Sheet (assets, liabilities, fund balance)",
}
# A few commonly cited specific object codes.
OBJECTS = {
    "1100": "Certificated Teachers' Salaries",
    "4700": "Food",
    "8011": "LCFF State Aid, Current Year",
}

# Function groups, keyed by leading digit, plus a few common specific codes.
FUNCTION_GROUPS = {
    "1": "Instruction",
    "2": "Instruction-related services",
    "3": "Pupil services",
    "4": "Ancillary services",
    "5": "Community services",
    "6": "Enterprise",
    "7": "General administration",
    "8": "Plant services",
    "9": "Other outgo",
}
FUNCTIONS = {
    "1000": "Instruction",
    "2420": "Instructional Library, Media and Technology",
    "2700": "School Administration",
    "3110": "Guidance and Counseling Services",
    "3140": "Health Services",
    "3600": "Pupil Transportation",
    "3700": "Food Services",
    "7200": "Other General Administration",
    "8100": "Plant Maintenance and Operations",
}

# Goal categories by inclusive range.
GOAL_RANGES = [
    (0, 0, "Undistributed (no instructional setting)"),
    (1, 999, "General Education, Pre-Kindergarten"),
    (1000, 1999, "General Education, K-12"),
    (3000, 3999, "School types (Alternative, Continuation, Juvenile Court, CTE, CPA)"),
    (4000, 4749, "General Education, Adult"),
    (4750, 4999, "Supplemental Education, K-12"),
    (5000, 5999, "Special Education"),
    (6000, 6999, "Regional Occupational Center / Program"),
    (7100, 7199, "Nonagency"),
    (8600, 8699, "County Services to Districts"),
    (9000, 9999, "Other Goals (locally defined)"),
]

# A couple of well-known Resource codes; the rest are described by band.
RESOURCES = {
    "0000": "Unrestricted / general purpose (no reporting requirement)",
    "3010": "Title I, Part A, Basic Grants (federal, restricted)",
}

_SEP = re.compile(r"[-\s./]+")


def resource_band(resource: str) -> str:
    """Return the restriction band for a 4-digit resource code."""
    n = int(resource)
    if 0 <= n <= 2999:
        return "Unrestricted"
    if 3000 <= n <= 5999:
        return "Federal, restricted"
    if 6000 <= n <= 8999:
        return "State, restricted"
    return "Local, restricted"


def _components(account_string: str) -> list[str]:
    """Split an account string into its six fields, or raise ValueError.

    Accepts either a delimited form (for example "01-0000-0-1110-1000-1100",
    separators may be hyphen, space, dot, or slash) or a packed 19-digit form
    ("0100000111010001100").
    """
    s = (account_string or "").strip()
    if not s:
        raise ValueError("empty account string")

    if _SEP.search(s):
        parts = _SEP.split(s)
        if len(parts) != len(FIELDS):
            raise ValueError(
                f"expected {len(FIELDS)} components (fund, resource, project year, "
                f"goal, function, object), got {len(parts)}: {parts}"
            )
        out: list[str] = []
        for (name, width), part in zip(FIELDS, parts):
            if not part.isdigit():
                raise ValueError(f"{name} '{part}' is not numeric")
            if len(part) != width:
                raise ValueError(f"{name} '{part}' must be {width} digit(s), got {len(part)}")
            out.append(part)
        return out

    # Packed form.
    if not s.isdigit():
        raise ValueError(f"packed account string must be digits only, got '{s}'")
    if len(s) != TOTAL_WIDTH:
        raise ValueError(f"packed account string must be {TOTAL_WIDTH} digits, got {len(s)}")
    out, i = [], 0
    for _, width in FIELDS:
        out.append(s[i : i + width])
        i += width
    return out


def validate(account_string: str) -> dict:
    """Validate a SACS account string structurally and against known codes.

    Returns a dict with `valid` (bool), `errors` (structural failures),
    `warnings` (unrecognized but possibly-valid codes), `components` (the six
    field values), and `normalized` (canonical hyphen-delimited form).
    """
    try:
        comps = _components(account_string)
    except ValueError as exc:
        return {
            "valid": False,
            "errors": [str(exc)],
            "warnings": [],
            "components": None,
            "normalized": None,
        }

    fund, resource, _py, goal, function, obj = comps
    warnings: list[str] = []
    if fund not in FUNDS:
        warnings.append(
            f"fund '{fund}' is not in the common-fund list (may still be valid; CDE publishes the full list)"
        )
    if obj[0] not in OBJECT_SERIES:
        warnings.append(f"object series '{obj[0]}xxx' is unrecognized")
    if function[0] not in FUNCTION_GROUPS:
        warnings.append(f"function group '{function[0]}xxx' is unrecognized")
    if not any(lo <= int(goal) <= hi for lo, hi, _ in GOAL_RANGES):
        warnings.append(f"goal '{goal}' falls outside the known goal ranges")

    return {
        "valid": True,
        "errors": [],
        "warnings": warnings,
        "components": dict(zip([name for name, _ in FIELDS], comps)),
        "normalized": "-".join(comps),
    }


def _goal_description(goal: str) -> str:
    n = int(goal)
    for lo, hi, desc in GOAL_RANGES:
        if lo <= n <= hi:
            return desc
    return "Unrecognized goal range"


def decode(account_string: str) -> dict:
    """Decode a SACS account string into its components with descriptions."""
    result = validate(account_string)
    if not result["valid"]:
        return result
    c = result["components"]
    decoded = {
        "fund": {"code": c["fund"], "description": FUNDS.get(c["fund"], "Fund (see CDE list)")},
        "resource": {
            "code": c["resource"],
            "band": resource_band(c["resource"]),
            "description": RESOURCES.get(c["resource"], f"{resource_band(c['resource'])} resource"),
        },
        "project_year": {
            "code": c["project_year"],
            "description": "No project year / not applicable"
            if c["project_year"] == "0"
            else f"Project or grant year {c['project_year']}",
        },
        "goal": {"code": c["goal"], "description": _goal_description(c["goal"])},
        "function": {
            "code": c["function"],
            "description": FUNCTIONS.get(
                c["function"], FUNCTION_GROUPS.get(c["function"][0], "Function (see CDE list)")
            ),
        },
        "object": {
            "code": c["object"],
            "description": OBJECTS.get(c["object"], OBJECT_SERIES.get(c["object"][0], "Object (see CDE list)")),
        },
    }
    return {
        "valid": True,
        "normalized": result["normalized"],
        "warnings": result["warnings"],
        "components": decoded,
    }


def list_codes(field: str) -> dict:
    """List the known codes for a SACS field.

    `field` is one of: fund, resource, project_year, goal, function, object.
    """
    f = (field or "").strip().lower().replace(" ", "_")
    if f == "fund":
        return {"field": "fund", "note": "Common funds, not exhaustive; see CDE.", "codes": FUNDS}
    if f == "object":
        return {"field": "object", "series_by_leading_digit": OBJECT_SERIES, "examples": OBJECTS}
    if f == "function":
        return {"field": "function", "groups_by_leading_digit": FUNCTION_GROUPS, "examples": FUNCTIONS}
    if f == "goal":
        return {
            "field": "goal",
            "ranges": [{"low": lo, "high": hi, "description": d} for lo, hi, d in GOAL_RANGES],
        }
    if f == "resource":
        return {
            "field": "resource",
            "bands": {
                "0000-2999": "Unrestricted",
                "3000-5999": "Federal, restricted",
                "6000-8999": "State, restricted",
                "9000-9999": "Local, restricted",
            },
            "examples": RESOURCES,
        }
    if f in ("project_year", "year"):
        return {
            "field": "project_year",
            "description": "1 digit. 0 = not applicable; 1-9 = grant or project year for multi-year resources.",
        }
    return {
        "field": field,
        "error": f"unknown field '{field}'. Use one of: fund, resource, project_year, goal, function, object.",
    }
