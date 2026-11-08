"""Quy đổi cách nói thời gian thành khoảng ngày, theo rulebook §2.

Mọi ``Period`` là khoảng ngày **đóng hai đầu** [start, end].
"""

from __future__ import annotations

import calendar as _calendar
from dataclasses import dataclass
from datetime import date, timedelta

import pandas as pd

__all__ = [
    "Period",
    "between",
    "day",
    "last_month_same_days",
    "last_n_days",
    "last_week",
    "month",
    "previous_month",
    "quarter",
    "same_month_last_year",
    "this_month",
    "this_week",
    "until",
    "year",
    "year_of_month",
    "year_to_date",
]  # đây cũng là toàn bộ những gì code LLM gọi được qua `P` (xem assets/prompts/toolkit.md)


@dataclass(frozen=True)
class Period:
    """Khoảng ngày đóng hai đầu [start, end]."""

    start: date
    end: date

    @property
    def days(self) -> int:
        return (self.end - self.start).days + 1

    def contains(self, column: pd.Series) -> pd.Series:
        """Mask cho cột datetime: ngày (bỏ giờ) nằm trong kỳ."""
        days = pd.to_datetime(column).dt.normalize()
        mask: pd.Series = (days >= pd.Timestamp(self.start)) & (days <= pd.Timestamp(self.end))
        return mask

    def shift_back(self) -> Period:
        """Kỳ liền trước có cùng số ngày."""
        end = self.start - timedelta(days=1)
        return Period(end - timedelta(days=self.days - 1), end)


def day(d: date) -> Period:
    """Kỳ một ngày."""
    return Period(d, d)


def year(year_: int) -> Period:
    """Cả năm dương lịch."""
    return Period(date(year_, 1, 1), date(year_, 12, 31))


def between(start: date, end: date) -> Period:
    """Khoảng ngày bất kỳ từ ``start`` đến hết ``end`` (cả hai đầu đều tính)."""
    return Period(start, end)


def month(year: int, month_: int) -> Period:
    """Cả tháng dương lịch."""
    last = _calendar.monthrange(year, month_)[1]
    return Period(date(year, month_, 1), date(year, month_, last))


def previous_month(year: int, month_: int) -> Period:
    """Tháng liền trước."""
    return month(year - 1, 12) if month_ == 1 else month(year, month_ - 1)


def same_month_last_year(year: int, month_: int) -> Period:
    """Cùng tháng của năm trước."""
    return month(year - 1, month_)


def year_of_month(month_: int, today: date) -> int:
    """'tháng M' không ghi năm: năm nay nếu không sau hôm nay, ngược lại năm trước."""
    return today.year if date(today.year, month_, 1) <= today else today.year - 1


def this_month(today: date) -> Period:
    """Từ ngày 1 đến hết hôm nay."""
    return Period(today.replace(day=1), today)


def last_month_same_days(today: date) -> Period:
    """Tháng trước, từ ngày 1 đến ngày trùng số với hôm nay (hoặc hết tháng trước)."""
    previous = previous_month(today.year, today.month)
    end_day = min(today.day, previous.end.day)
    return Period(previous.start, previous.start.replace(day=end_day))


def this_week(today: date) -> Period:
    """Từ thứ Hai của tuần chứa hôm nay đến hết hôm nay."""
    return Period(today - timedelta(days=today.weekday()), today)


def last_week(today: date) -> Period:
    """Cả tuần liền trước, thứ Hai đến Chủ nhật."""
    monday = today - timedelta(days=today.weekday() + 7)
    return Period(monday, monday + timedelta(days=6))


def last_n_days(today: date, n: int) -> Period:
    """N ngày liền nhau, ngày cuối là hôm nay."""
    return Period(today - timedelta(days=n - 1), today)


def quarter(year: int, q: int) -> Period:
    """Cả quý (1 đến 4)."""
    start = month(year, 3 * q - 2)
    return Period(start.start, month(year, 3 * q).end)


def year_to_date(today: date) -> Period:
    """Từ 1/1 đến hết hôm nay."""
    return Period(date(today.year, 1, 1), today)


def until(d: date, data_start: date) -> Period:
    """'Đến hết ngày X': mọi phát sinh từ đầu dữ liệu đến hết ngày X."""
    return Period(data_start, d)
