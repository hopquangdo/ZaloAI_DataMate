import pytest

from datamate.modules.domain.business_rules import pct, pct_change, round_money


def test_round_money_rounds_half_up() -> None:
    assert round_money(10.5) == 11
    assert round_money(10.49) == 10


def test_pct_and_pct_change() -> None:
    assert pct(1, 3) == 33.33
    assert pct_change(90, 100) == -10.0


def test_zero_denominator_is_an_error_not_infinity() -> None:
    with pytest.raises(ZeroDivisionError):
        pct(1, 0)
    with pytest.raises(ZeroDivisionError):
        pct_change(1, 0)
