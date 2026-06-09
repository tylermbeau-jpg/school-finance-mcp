from school_finance_mcp import sacs

VALID = "01-0000-0-1110-1000-1100"
PACKED = "0100000111010001100"


def test_total_width_is_19():
    assert sacs.TOTAL_WIDTH == 19


def test_validate_accepts_valid_delimited():
    r = sacs.validate(VALID)
    assert r["valid"] is True
    assert r["errors"] == []
    assert r["components"]["fund"] == "01"
    assert r["components"]["object"] == "1100"


def test_validate_accepts_packed_19_digits():
    r = sacs.validate(PACKED)
    assert r["valid"] is True
    assert r["normalized"] == VALID


def test_validate_rejects_wrong_field_width():
    r = sacs.validate("1-0000-0-1110-1000-1100")  # fund is one digit
    assert r["valid"] is False
    assert r["errors"]


def test_validate_rejects_non_numeric():
    r = sacs.validate("01-00X0-0-1110-1000-1100")
    assert r["valid"] is False


def test_validate_rejects_wrong_packed_length():
    r = sacs.validate("12345")
    assert r["valid"] is False


def test_decode_returns_components_with_descriptions():
    d = sacs.decode(VALID)
    assert d["valid"] is True
    c = d["components"]
    assert c["fund"]["description"] == "General Fund"
    assert c["object"]["description"] == "Certificated Teachers' Salaries"
    assert c["goal"]["description"] == "General Education, K-12"
    assert c["resource"]["band"] == "Unrestricted"
    assert c["project_year"]["description"].startswith("No project year")


def test_decode_cafeteria_food_string():
    d = sacs.decode("13-5310-0-0000-3700-4700")
    c = d["components"]
    assert c["fund"]["description"] == "Cafeteria Special Revenue Fund"
    assert c["function"]["description"] == "Food Services"
    assert c["object"]["description"] == "Food"
    assert c["resource"]["band"] == "Federal, restricted"


def test_list_codes_fund_and_unknown_field():
    assert "01" in sacs.list_codes("fund")["codes"]
    assert "error" in sacs.list_codes("widget")
