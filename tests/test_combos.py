from school_finance_mcp import combos, sacs


def codes(s):
    f, r, _py, g, fn, o = s.split("-")
    return {"fund": f, "resource": r, "goal": g, "function": fn, "object": o}


def test_two_table_years_on_file_and_year_parsing():
    assert combos.available_years() == ["2025", "2026"]
    assert combos.table_year("2025-26") == "2025"
    assert combos.table_year("2026") == "2026"
    assert combos.table_year(None) == "2026"
    assert combos.table_year("2027-28") is None


def test_clean_general_fund_teacher_string_passes_every_applicable_check():
    r = combos.check(codes("01-0000-0-1110-1000-1100"))
    assert r["tables"] == "2026-27"
    assert r["code_errors"] == [] and r["combination_errors"] == []
    assert set(r["passed"]) >= {"CHK-FUNDxRESOURCE", "CHK-FUNDxGOAL", "CHK-FUNDxFUNCTION-B",
                                "CHK-FUNDxOBJECT", "CHK-FUNCTIONxOBJECT", "CHK-GOALxFUNCTION-A"}


def test_cafeteria_resource_is_valid_in_fund_13_and_not_in_fund_21():
    ok = combos.check(codes("13-5310-0-0000-3700-4700"))
    assert ok["combination_errors"] == []
    bad = combos.check(codes("21-5310-0-0000-3700-4700"))
    ids = [e["check"] for e in bad["combination_errors"]]
    assert "CHK-FUNDxRESOURCE" in ids
    fr = next(e for e in bad["combination_errors"] if e["check"] == "CHK-FUNDxRESOURCE")
    assert fr["severity"] == "W" and fr["severity_word"] == "warning"
    assert fr["codes"] == {"fund": "21", "resource": "5310"}


def test_instruction_function_needs_an_instructional_goal():
    r = combos.check(codes("01-0000-0-0000-1000-1100"))
    assert [e["check"] for e in r["combination_errors"]] == ["CHK-GOALxFUNCTION-A"]
    assert r["combination_errors"][0]["severity"] == "F"


def test_teacher_salaries_cannot_sit_under_general_administration():
    r = combos.check(codes("01-0000-0-1110-7200-1100"))
    ids = {e["check"] for e in r["combination_errors"]}
    assert ids == {"CHK-FUNCTIONxOBJECT", "CHK-GOALxFUNCTION-B"}


def test_unknown_resource_fails_checkresource_and_skips_its_combinations():
    r = combos.check(codes("01-9999-0-1110-1000-1100"))
    assert [e["check"] for e in r["code_errors"]] == ["CHECKRESOURCE"]
    assert r["combination_errors"] == []
    assert set(r["not_evaluated"]) == {"CHK-FUNDxRESOURCE", "CHK-RESOURCExOBJECTB"}


def test_goal_x_function_is_out_of_scope_for_revenue_objects():
    r = combos.check(codes("01-3010-0-1110-1000-8290"))
    assert "CHK-GOALxFUNCTION-A" not in r["passed"]
    assert "CHK-GOALxFUNCTION-A" not in [e["check"] for e in r["combination_errors"]]
    assert "CHK-RESOURCExOBJECTA" in r["passed"]


def test_beginning_balance_object_is_exempt_from_resource_x_object():
    r = combos.check(codes("01-0000-0-1110-1000-9791"))
    assert not any(c.startswith("CHK-RESOURCExOBJECT") for c in r["passed"] + r["not_covered"])
    assert r["combination_errors"] == []


def test_unknown_fiscal_year_returns_an_error_entry_not_an_exception():
    r = combos.check(codes("01-0000-0-1110-1000-1100"), "2027-28")
    assert r["tables"] is None and "2025-26" in r["error"] and "2026-27" in r["error"]


def test_validate_integrates_cde_checks_and_prior_year_tables():
    r = sacs.validate("21-5310-0-0000-3700-4700")
    assert r["valid"] is False and r["errors"] == []
    assert r["tables"] == "2026-27"
    assert any(e["check"] == "CHK-FUNDxRESOURCE" for e in r["cde_checks"]["combination_errors"])
    prior = sacs.validate("01-0000-0-1110-1000-1100", fiscal_year="2025-26")
    assert prior["valid"] is True and prior["tables"] == "2025-26"


def test_list_codes_returns_cde_full_fund_list():
    r = sacs.list_codes("fund")
    assert r["tables"] == "2026-27" and len(r["codes"]) == 34 and "13" in r["codes"]
    assert "General Fund" in r["common_funds"].values()
