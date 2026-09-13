from datetime import date
from decimal import Decimal

from backend.analytics.query_service import _percent, _shift_months


def test_percent_rounds_half_up_to_two_decimals():
    assert _percent(Decimal("2"), Decimal("3")) == Decimal("66.67")


def test_percent_returns_none_for_zero_denominator():
    assert _percent(Decimal("10"), Decimal("0")) is None


def test_yoy_month_shift_handles_leap_day():
    assert _shift_months(date(2024, 2, 29), -12) == date(2023, 2, 28)


def test_qoq_month_shift_crosses_year_boundary():
    assert _shift_months(date(2026, 2, 1), -3) == date(2025, 11, 1)
