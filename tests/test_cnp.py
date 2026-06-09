from school_finance_mcp import cnp


def test_school_year_label():
    assert cnp.calculate_meal_reimbursement(free_lunches=1)["school_year"] == "2025-26"


def test_federal_free_lunch_only():
    r = cnp.calculate_meal_reimbursement(free_lunches=100)
    assert abs(r["total_reimbursement"] - 460.00) < 0.005


def test_performance_based_adds_nine_cents_per_lunch():
    r = cnp.calculate_meal_reimbursement(free_lunches=100, performance_based=True)
    assert abs(r["total_reimbursement"] - 469.00) < 0.005


def test_high_isp_lunch_tier():
    r = cnp.calculate_meal_reimbursement(free_lunches=100, high_isp=True)
    assert abs(r["total_reimbursement"] - 462.00) < 0.005


def test_severe_need_breakfast_tier():
    r = cnp.calculate_meal_reimbursement(free_breakfasts=100, severe_need_breakfast=True)
    assert abs(r["total_reimbursement"] - 294.00) < 0.005


def test_mixed_lunch_categories():
    # 50*4.60 + 10*4.20 + 40*0.44 = 230 + 42 + 17.60 = 289.60
    r = cnp.calculate_meal_reimbursement(free_lunches=50, reduced_lunches=10, paid_lunches=40)
    assert abs(r["total_reimbursement"] - 289.60) < 0.005


def test_california_universal_meals_paid_lunch():
    # federal 100*0.44 = 44.00; free-rate topup 100*(4.60-0.44) = 416.00;
    # state per meal 100*1.0015 = 100.15; total = 560.15
    r = cnp.calculate_meal_reimbursement(paid_lunches=100, california_universal_meals=True)
    assert abs(r["federal"]["subtotal"] - 44.00) < 0.005
    assert abs(r["california_state"]["subtotal"] - 516.15) < 0.005
    assert abs(r["total_reimbursement"] - 560.15) < 0.005
