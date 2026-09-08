"""CDE valid-code and valid-combination checks for a single SACS account string.

The California Department of Education publishes, for each fiscal year, the
list of valid codes for every SACS dimension and seven matrices saying which
codes may be combined (Fund x Resource, Fund x Goal, Fund x Function,
Fund x Object, Function x Object, Resource x Object, Goal x Function). The
SACS technical review (TRC) applies those tables under check ids such as
CHK-FUNDxRESOURCE. This module applies the same tables to one string and
reports findings under the same ids, so a result compares directly with the
TRC screen.

Data: data/combos_<year>.json, generated from CDE's valid-combination
spreadsheets (https://www.cde.ca.gov/fg/ac/ac/sprvalidcombs.asp). A cell
counts as valid when CDE marks it valid for school districts. The file for
year N holds the tables for fiscal year N to N+1 (combos_2025.json is 2025-26).

Scope: this is the check, not the fix. It does not propose replacement codes,
check balances or transfers, or read whole export files.
"""

from __future__ import annotations

import json
import re
from functools import lru_cache
from pathlib import Path

DATA_DIR = Path(__file__).resolve().parent / "data"

DIMS = ("fund", "resource", "goal", "function", "object")
DIM_LABELS = {"fund": "Fund", "resource": "Resource", "goal": "Goal",
              "function": "Function", "object": "Object"}
CODE_CHECK = {"fund": "CHECKFUND", "resource": "CHECKRESOURCE", "goal": "CHECKGOAL",
              "function": "CHECKFUNCTION", "object": "CHECKOBJECT"}

# CDE severity for each check id: F fatal (blocks the official export),
# W warning (needs an explanation), O informational.
SEVERITY = {
    "CHECKFUND": "F", "CHECKRESOURCE": "W", "CHECKGOAL": "F",
    "CHECKFUNCTION": "F", "CHECKOBJECT": "F",
    "CHK-FUNDxRESOURCE": "W", "CHK-FUNDxGOAL": "W",
    "CHK-FUNDxFUNCTION-A": "W", "CHK-FUNDxFUNCTION-B": "F",
    "CHK-FUNDxOBJECT": "F", "CHK-FUNCTIONxOBJECT": "F",
    "CHK-GOALxFUNCTION-A": "F", "CHK-GOALxFUNCTION-B": "F",
    "CHK-RESOURCExOBJECTA": "W", "CHK-RESOURCExOBJECTB": "O",
}
SEVERITY_WORD = {"F": "fatal", "W": "warning", "O": "informational"}

# Beginning-balance objects that CDE exempts from the resource x object check.
BEGIN_BALANCE_OBJECTS = {"9791", "9793", "9795"}
# Funds where an invalid fund x function pairing is fatal rather than a warning.
GENERAL_FUND_LIKE = {"01", "09", "62"}


def available_years() -> list[str]:
    """Table years on file, oldest first (a year N file covers N to N+1)."""
    return sorted(p.stem.split("_")[1] for p in DATA_DIR.glob("combos_*.json"))


def table_year(fiscal_year: str | None) -> str | None:
    """Map a fiscal year label to a table year, or None when nothing matches.

    Accepts "2025-26", "2025-2026", "2025", "26" style input. None or an empty
    value selects the latest tables on file.
    """
    years = available_years()
    if not years:
        return None
    if fiscal_year is None or not str(fiscal_year).strip():
        return years[-1]
    m = re.match(r"^\s*(\d{4})", str(fiscal_year))
    if not m:
        return None
    year = m.group(1)
    return year if year in years else None


def fiscal_label(year: str) -> str:
    return f"{year}-{str(int(year) + 1)[-2:]}"


@lru_cache(maxsize=8)
def load(year: str) -> dict:
    return json.loads((DATA_DIR / f"combos_{year}.json").read_text())


def scope_of(key: str, codes: dict) -> str | None:
    """The CDE check a failure of matrix `key` is reported under for these codes,
    or None when CDE does not apply that matrix to this string."""
    obj = codes["object"]
    o, fn = int(obj), int(codes["function"])
    if key == "fund_resource":
        return "CHK-FUNDxRESOURCE"
    if key == "fund_goal":
        return "CHK-FUNDxGOAL"
    if key == "fund_function":
        return "CHK-FUNDxFUNCTION-B" if codes["fund"] in GENERAL_FUND_LIKE else "CHK-FUNDxFUNCTION-A"
    if key == "fund_object":
        return "CHK-FUNDxOBJECT"
    if key == "function_object":
        return "CHK-FUNCTIONxOBJECT"
    if key == "object_resource":
        if obj in BEGIN_BALANCE_OBJECTS:
            return None
        if 8000 <= o <= 9999:
            return "CHK-RESOURCExOBJECTA"
        if 1000 <= o <= 7999:
            return "CHK-RESOURCExOBJECTB"
        return None
    if key == "goal_function":
        if not 1000 <= o <= 7999:
            return None
        if 1000 <= fn <= 1999 or 4000 <= fn <= 5999:
            return "CHK-GOALxFUNCTION-A"
        if 7200 <= fn <= 7999 and fn != 7210:
            return "CHK-GOALxFUNCTION-B"
        return None
    return None


def pair_state(matrix: dict, dims: dict, col: str, row: str) -> bool | None:
    """True when the pair is valid, False when invalid, None when the matrix
    does not cover these (known) codes and so makes no claim."""
    if row not in dims[matrix["rowDim"]] or col not in dims[matrix["colDim"]]:
        return False
    if row not in matrix["rows"] or col not in matrix["cols"]:
        return None
    return matrix["cols"].index(col) in matrix["classes"][matrix["rows"][row]]


def _finding(check: str, dims_involved: list[str], codes: dict, message: str) -> dict:
    return {
        "check": check,
        "severity": SEVERITY.get(check, "W"),
        "severity_word": SEVERITY_WORD[SEVERITY.get(check, "W")],
        "dimensions": dims_involved,
        "codes": {d: codes[d] for d in dims_involved},
        "message": message,
    }


def check(codes: dict, fiscal_year: str | None = None) -> dict:
    """Run CDE's code and combination checks on one string's codes.

    `codes` holds fund, resource, goal, function, object (project year is not
    part of any CDE table). Returns the table year used, code errors,
    combination errors, the checks that passed, pairs the tables do not cover,
    and checks that could not be evaluated because a code is not valid.
    """
    year = table_year(fiscal_year)
    if year is None:
        wanted = fiscal_year if fiscal_year else "latest"
        return {
            "tables": None,
            "error": (
                f"No CDE combination tables on file for fiscal year '{wanted}'. "
                f"Years available: {', '.join(fiscal_label(y) for y in available_years())}."
            ),
            "code_errors": [], "combination_errors": [], "passed": [],
            "not_covered": [], "not_evaluated": [],
        }
    data = load(year)
    dims, matrices = data["dims"], data["matrices"]
    result = {
        "tables": fiscal_label(year),
        "code_errors": [], "combination_errors": [], "passed": [],
        "not_covered": [], "not_evaluated": [],
    }
    bad = set()
    for d in DIMS:
        if codes[d] not in dims[d]:
            bad.add(d)
            result["code_errors"].append(_finding(
                CODE_CHECK[d], [d], codes,
                f"{DIM_LABELS[d]} {codes[d]} is not a valid {fiscal_label(year)} code "
                f"(retired, new-year-only, or a typo).",
            ))
    for key, m in matrices.items():
        cid = scope_of(key, codes)
        if cid is None:
            continue
        col_dim, row_dim = m["colDim"], m["rowDim"]
        involved = [col_dim, row_dim] if key != "object_resource" else [row_dim, col_dim]
        if col_dim in bad or row_dim in bad:
            result["not_evaluated"].append(cid)
            continue
        state = pair_state(m, dims, codes[col_dim], codes[row_dim])
        if state is None:
            result["not_covered"].append(cid)
        elif state:
            result["passed"].append(cid)
        else:
            a, b = involved
            result["combination_errors"].append(_finding(
                cid, involved, codes,
                f"{DIM_LABELS[a]} {codes[a]} is not valid with {DIM_LABELS[b]} {codes[b]} "
                f"in CDE's {fiscal_label(year)} tables.",
            ))
    return result


def valid_codes(field: str, fiscal_year: str | None = None) -> dict:
    """CDE's full valid-code list for one dimension."""
    year = table_year(fiscal_year)
    if year is None:
        return {"field": field, "error": "no CDE tables on file for that fiscal year",
                "years_available": [fiscal_label(y) for y in available_years()]}
    return {"field": field, "tables": fiscal_label(year), "codes": list(load(year)["dims"][field])}
