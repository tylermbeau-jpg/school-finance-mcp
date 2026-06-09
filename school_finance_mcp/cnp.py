"""School-meal reimbursement rates and calculator (federal + California).

Rates below are public figures for school year 2025-26:
- Federal National Average Payment rates (USDA FNS, effective July 1, 2025
  through June 30, 2026, contiguous 48 states and DC).
- California Universal Meals state per-meal reimbursement (Proposition 98).

This is illustrative. Verify current rates and apportionment rules against
USDA FNS and the CDE before official use. See README for sources.
"""

from __future__ import annotations

SCHOOL_YEAR = "2025-26"

# Federal National School Lunch Program rates by tier and category.
# "standard" applies to LEAs below 60% free/reduced; "high_isp" to 60% or above.
FEDERAL_LUNCH = {
    "standard": {"free": 4.60, "reduced": 4.20, "paid": 0.44},
    "high_isp": {"free": 4.62, "reduced": 4.22, "paid": 0.46},
}
# Federal School Breakfast Program rates by tier and category.
FEDERAL_BREAKFAST = {
    "standard": {"free": 2.46, "reduced": 2.16, "paid": 0.40},
    "severe_need": {"free": 2.94, "reduced": 2.64, "paid": 0.40},
}
# Additional federal cents per lunch for performance-certified SFAs.
PERFORMANCE_BASED_LUNCH = 0.09
# California Universal Meals state per-meal reimbursement (Prop 98), SY 2025-26.
CA_STATE_PER_MEAL = 1.0015

CATEGORIES = ("free", "reduced", "paid")


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
    """Compute meal reimbursement from counts of lunches and breakfasts.

    Federal reimbursement uses the SY 2025-26 NSLP/SBP rate tables. Set
    `high_isp=True` for the 60%-or-above lunch tier, `severe_need_breakfast=True`
    for the severe-need breakfast tier, and `performance_based=True` to add the
    extra 9 cents per lunch for certified SFAs.

    When `california_universal_meals=True`, the model adds the California
    contribution: every reimbursable meal is funded to the federal free rate
    (the state covers the gap for reduced and paid meals), plus the state
    per-meal reimbursement. This is a simplified model of the program; exact
    apportionment has additional rules.
    """
    lunch_tier = "high_isp" if high_isp else "standard"
    breakfast_tier = "severe_need" if severe_need_breakfast else "standard"
    lunch_rates = FEDERAL_LUNCH[lunch_tier]
    breakfast_rates = FEDERAL_BREAKFAST[breakfast_tier]

    lunches = {"free": free_lunches, "reduced": reduced_lunches, "paid": paid_lunches}
    breakfasts = {"free": free_breakfasts, "reduced": reduced_breakfasts, "paid": paid_breakfasts}

    federal_lunch = sum(lunches[c] * lunch_rates[c] for c in CATEGORIES)
    federal_breakfast = sum(breakfasts[c] * breakfast_rates[c] for c in CATEGORIES)
    total_lunches = sum(lunches.values())
    total_breakfasts = sum(breakfasts.values())
    perf = total_lunches * PERFORMANCE_BASED_LUNCH if performance_based else 0.0
    federal = federal_lunch + federal_breakfast + perf

    free_rate_topup = 0.0
    state_per_meal = 0.0
    if california_universal_meals:
        free_rate_topup += sum(lunches[c] * (lunch_rates["free"] - lunch_rates[c]) for c in ("reduced", "paid"))
        free_rate_topup += sum(
            breakfasts[c] * (breakfast_rates["free"] - breakfast_rates[c]) for c in ("reduced", "paid")
        )
        state_per_meal = (total_lunches + total_breakfasts) * CA_STATE_PER_MEAL
    california_state = free_rate_topup + state_per_meal
    total = federal + california_state

    def r(value: float) -> float:
        return round(value, 2)

    return {
        "school_year": SCHOOL_YEAR,
        "rate_tier": {"lunch": lunch_tier, "breakfast": breakfast_tier},
        "meal_counts": {"lunches": total_lunches, "breakfasts": total_breakfasts},
        "federal": {
            "lunch": r(federal_lunch),
            "breakfast": r(federal_breakfast),
            "performance_based": r(perf),
            "subtotal": r(federal),
        },
        "california_state": {
            "free_rate_topup": r(free_rate_topup),
            "state_per_meal": r(state_per_meal),
            "subtotal": r(california_state),
        },
        "total_reimbursement": r(total),
        "disclaimer": (
            "SY 2025-26 USDA FNS and CDE published figures. Verify current rates "
            "and apportionment rules with USDA FNS and the CDE before official use."
        ),
    }
