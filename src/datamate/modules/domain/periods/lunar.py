"""Lịch âm (từ calendar.csv của đề) và các kỳ dịp Tết, theo rulebook §2."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from pathlib import Path

import pandas as pd

from datamate.modules.domain.periods.period import Period


@dataclass(frozen=True)
class LunarCalendar:
    """Bảng quy đổi ngày dương sang âm từ calendar.csv, và kỳ Tết."""

    table: pd.DataFrame  # cột: date, lunar_day, lunar_month, lunar_year, lunar_leap

    @classmethod
    def load(cls, path: Path) -> LunarCalendar:
        table = pd.read_csv(path, parse_dates=["date"])
        table["lunar_leap"] = table["lunar_leap"].astype(str).str.lower() == "true"
        return cls(table)

    def solar(self, lunar_year: int, lunar_month: int, lunar_day: int) -> date:
        rows = self.table[
            (self.table["lunar_year"] == lunar_year)
            & (self.table["lunar_month"] == lunar_month)
            & (self.table["lunar_day"] == lunar_day)
            & ~self.table["lunar_leap"]
        ]
        if rows.empty:
            raise LookupError(f"Không có ngày âm {lunar_day}/{lunar_month}/{lunar_year} trong lịch")
        return rows["date"].iloc[0].date()  # type: ignore[no-any-return]

    def tet(self, year: int) -> Period:
        """Tết năm Y: 23 tháng Chạp (năm âm Y−1) → hết mùng 10 tháng Giêng (năm âm Y)."""
        return Period(self.solar(year - 1, 12, 23), self.solar(year, 1, 10))

    def before_tet(self, year: int) -> Period:
        """Cùng số ngày ngay trước 23 tháng Chạp."""
        return self.tet(year).shift_back()
