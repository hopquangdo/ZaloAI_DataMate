from datetime import date
from pathlib import Path

import pandas as pd
import pytest

from datamate.modules.domain.periods import LunarCalendar
from datamate.modules.domain.periods import period as P  # noqa: N812

CALENDAR = Path("dataset/train/train/calendar.csv")


def test_weeks_start_on_monday() -> None:
    wednesday = date(2026, 3, 4)
    assert P.this_week(wednesday) == P.Period(date(2026, 3, 2), wednesday)
    assert P.last_week(wednesday) == P.Period(date(2026, 2, 23), date(2026, 3, 1))


def test_this_month_compared_with_same_days_last_month() -> None:
    today = date(2026, 3, 31)
    assert P.this_month(today) == P.Period(date(2026, 3, 1), today)
    assert P.last_month_same_days(today) == P.Period(date(2026, 2, 1), date(2026, 2, 28))


def test_month_without_year_goes_back_when_in_the_future() -> None:
    assert P.year_of_month(9, date(2026, 3, 4)) == 2025
    assert P.year_of_month(3, date(2026, 3, 4)) == 2026


def test_last_n_days_and_quarter() -> None:
    assert P.last_n_days(date(2026, 3, 4), 7).start == date(2026, 2, 26)
    assert P.quarter(2025, 4) == P.Period(date(2025, 10, 1), date(2025, 12, 31))


def test_contains_ignores_time_of_day() -> None:
    column = pd.Series(pd.to_datetime(["2026-03-01 23:59", "2026-03-02 00:01"]))
    assert P.day(date(2026, 3, 1)).contains(column).tolist() == [True, False]


@pytest.mark.skipif(not CALENDAR.exists(), reason="cần dataset")
def test_tet_uses_lunar_calendar() -> None:
    lunar = LunarCalendar.load(CALENDAR)
    tet_2025 = lunar.tet(2025)  # mùng 1 Tết Ất Tỵ: 29/01/2025
    assert tet_2025.start == date(2025, 1, 22)
    assert tet_2025.end == date(2025, 2, 7)
    assert lunar.before_tet(2025).end == date(2025, 1, 21)
