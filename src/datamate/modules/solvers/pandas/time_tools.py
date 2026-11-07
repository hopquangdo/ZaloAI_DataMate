"""Bọc ``P`` (kỳ thời gian) và ``lunar`` cho code LLM: nhận ngày nhiều dạng, trả ``pd.Timestamp``.

Lý do: model nhỏ hay viết ``P.day(2025, 10, 19)`` thay vì ``P.day(date(...))``, và hay so cột
``datetime64`` với ``datetime.date`` (pandas báo lỗi). Bọc lại để cả hai cách viết đều chạy:
- đầu vào: ``date`` / ``datetime`` / ``pd.Timestamp`` / chuỗi ISO đều được đổi về ``date``;
  ``P.day(y, m, d)`` được hiểu là ``P.day(date(y, m, d))``;
- đầu ra: ``Period`` có ``start`` / ``end`` là ``pd.Timestamp``, ngày đơn lẻ cũng vậy,
  nên so sánh trực tiếp với cột ngày được.
Logic tính kỳ vẫn nằm ở ``domain.periods`` (không đổi).
"""

from __future__ import annotations

import re
from collections.abc import Callable
from datetime import date, datetime, timedelta
from typing import Any

import pandas as pd

from datamate.modules.domain.periods import Period, period

_ISO_DATE = re.compile(r"^\d{4}-\d{2}-\d{2}")


def as_date(value: Any) -> Any:
    """Đổi giá trị dạng ngày về ``datetime.date``; giá trị khác giữ nguyên."""
    if isinstance(value, (pd.Timestamp, datetime)):
        return value.date()
    if isinstance(value, str) and _ISO_DATE.match(value):
        return date.fromisoformat(value[:10])
    return value


def as_timestamp(value: Any) -> Any:
    """Kết quả cho code LLM: ``Period`` / ``date`` → dùng ``pd.Timestamp``."""
    if isinstance(value, Period):
        return Period(pd.Timestamp(value.start), pd.Timestamp(value.end))
    if isinstance(value, date) and not isinstance(value, datetime):
        return pd.Timestamp(value)
    return value


def _wrap(name: str, fn: Callable[..., Any]) -> Callable[..., Any]:
    def call(*args: Any, **kwargs: Any) -> Any:
        if name == "day" and len(args) == 3 and all(isinstance(a, int) for a in args):
            args = (date(*args),)
        if name != "Period":
            args = tuple(as_date(a) for a in args)
            kwargs = {k: as_date(v) for k, v in kwargs.items()}
        return as_timestamp(fn(*args, **kwargs))

    call.__name__ = name
    call.__doc__ = fn.__doc__
    return call


class PeriodTools:
    """Thay cho module ``period`` trong namespace: cùng tên hàm, đầu vào / đầu ra dễ dùng hơn."""

    def __init__(self) -> None:
        for name in period.__all__:
            setattr(self, name, _wrap(name, getattr(period, name)))
        # tên model nhỏ hay tự nghĩ ra: cho chạy luôn thay vì báo lỗi
        previous = _wrap("previous_day", lambda d: period.day(d - timedelta(days=1)))
        self.previous_day = previous
        self.yesterday = previous

    def __getattr__(self, name: str) -> Any:
        available = ", ".join(sorted(period.__all__))
        raise AttributeError(f"P không có '{name}'. Các hàm có sẵn: {available}")


class LunarTools:
    """Bọc lịch âm: kết quả trả về dạng ``pd.Timestamp`` như ``PeriodTools``."""

    def __init__(self, lunar: Any) -> None:
        self._lunar = lunar

    def __getattr__(self, name: str) -> Any:
        attr = getattr(self._lunar, name)
        return _wrap(name, attr) if callable(attr) else attr
