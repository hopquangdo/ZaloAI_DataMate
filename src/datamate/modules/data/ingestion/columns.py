"""Đặt kiểu cho cột của bảng đã có header: ngày → datetime64, số → float, còn lại là chuỗi.

Mọi quy tắc đều tổng quát (dựa trên hình dạng dữ liệu và tên cột), không có nhánh riêng
cho doanh nghiệp nào.
"""

from __future__ import annotations

import re
from collections.abc import Callable
from typing import Any

import pandas as pd

from datamate.core.text import fold
from datamate.modules.data.ingestion.values import parse_datetime, parse_number

_MIN_PARSE_RATIO = 0.9
_ZERO_PADDED_DIGITS = re.compile(r"^0\d{5,}$")  # số điện thoại, mã — giữ dạng chữ
_DATE_NAME = re.compile(
    r"ngay|thoi gian|thoi diem|\bgio\b|date|time|\bhsd\b|han (su dung|tra|thanh)"
)
_TEXT_NAME = re.compile(
    r"\bma\b|\bso (phieu|ct|hd|chung tu|kh)\b|dien thoai|phone|di dong|\bsdt\b|\bmst\b|cccd|cmnd"
    r"|barcode|\bean\b|\bsku\b|\bid\b|\blo\b|bien so|so dien thoai"
)


def column_words(name: str) -> str:
    """'ThoiGianLap' / 'Thời gian_lập' → 'thoi gian lap' để khớp từ khoá."""
    chars: list[str] = []
    for previous, char in zip(" " + name[:-1], name, strict=True):
        if char.isupper() and previous.islower():
            chars.append(" ")
        chars.append(" " if char == "_" else char)
    return fold("".join(chars))


def _map_unique(series: pd.Series, parser: Callable[[Any], Any]) -> pd.Series:
    """Parse mỗi giá trị khác nhau một lần (cột lớn có rất nhiều giá trị lặp)."""
    cache: dict[Any, Any] = {}

    def parse(value: Any) -> Any:
        key = (type(value), value)
        if key not in cache:
            cache[key] = parser(value)
        return cache[key]

    return series.map(parse, na_action="ignore")


def _enough_parsed(original: pd.Series, parsed: pd.Series) -> bool:
    present = original.notna()
    return bool(present.any()) and parsed[present].notna().mean() >= _MIN_PARSE_RATIO


def _as_number(series: pd.Series) -> pd.Series | None:
    if series.dropna().astype(str).str.match(_ZERO_PADDED_DIGITS).mean() > 0.5:
        return None
    parsed = _map_unique(series, parse_number)
    return parsed.astype(float) if _enough_parsed(series, parsed) else None


def _as_datetime(series: pd.Series, default_year: pd.Series | None) -> pd.Series | None:
    if default_year is None or default_year.isna().all():
        parsed = _map_unique(series, parse_datetime)
    else:
        pairs = pd.Series(list(zip(series, default_year, strict=True)), index=series.index)
        parsed = _map_unique(
            pairs,
            lambda pair: parse_datetime(pair[0], None if pd.isna(pair[1]) else int(pair[1])),
        )
        parsed[series.isna()] = None
    return pd.to_datetime(parsed) if _enough_parsed(series, parsed) else None


def _is_text_column(series: pd.Series) -> bool:
    return bool(series.dropna().map(lambda v: isinstance(v, str)).any())


def type_column(name: str, series: pd.Series, default_year: pd.Series | None) -> pd.Series:
    """Cột ngày → datetime64; cột số → float; còn lại giữ chuỗi đã strip."""
    words = column_words(name)
    if _DATE_NAME.search(words) and (dates := _as_datetime(series, default_year)) is not None:
        return dates
    if not _is_text_column(series):
        numeric = pd.to_numeric(series, errors="coerce")
        return numeric.astype(float) if numeric.notna().sum() == series.notna().sum() else series
    if not _TEXT_NAME.search(words):
        if (numbers := _as_number(series)) is not None:
            return numbers
        if (dates := _as_datetime(series, default_year)) is not None:
            return dates
    return series.map(lambda v: v.strip() if isinstance(v, str) else v)


def type_columns(table: pd.DataFrame, default_year: pd.Series | None = None) -> pd.DataFrame:
    """Đặt kiểu cho mọi cột của bảng."""
    typed: pd.DataFrame = pd.DataFrame(
        {name: type_column(str(name), table[name], default_year) for name in table.columns},
        index=table.index,
    )
    return typed
