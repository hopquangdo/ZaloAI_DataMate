"""Parse giá trị ô bẩn: tiền ("1tr440", "396k", "55.000đ"), số lượng ("3 chai"), ngày.

Mọi hàm trả ``None`` khi không parse được, không ném lỗi: cột chỉ được đổi kiểu
khi đa số giá trị parse được (xem ``tables.py``).
"""

from __future__ import annotations

import math
import re
from datetime import date, datetime, timedelta
from typing import Any

_EXCEL_EPOCH = date(1899, 12, 30)
_EXCEL_SERIAL_RANGE = (20000, 80000)  # ~1954 .. ~2119

_CURRENCY = re.compile(r"(vnđ|vnd|đồng|dong|đ|₫)$")
_MILLION = re.compile(r"^(\d+(?:[.,]\d+)?)\s*(?:tr|triệu|trieu)\s*(\d*)$")
_THOUSAND = re.compile(r"^(\d+(?:[.,]\d+)?)\s*(?:k|nghìn|nghin|ngàn|ngan)$")
_PLAIN = re.compile(r"^[+-]?\d[\d.,]*$")
_LEADING_NUMBER = re.compile(r"^([+-]?\d[\d.,]*)\s*[^\W\d_][^\W\d_ ]*$")  # "3 chai", "2 thùng"

_ISO = re.compile(r"^(\d{4})-(\d{1,2})-(\d{1,2})(?:[ T](\d{1,2}):(\d{2})(?::(\d{2}))?)?")
_DMY = re.compile(r"^(\d{1,2})[/.-](\d{1,2})[/.-](\d{4})(?:\s+(\d{1,2}):(\d{2})(?::(\d{2}))?)?$")
_DM = re.compile(r"^(\d{1,2})/(\d{1,2})$")
_VN_MONTH = re.compile(r"^(\d{1,2})\s+thg\s+(\d{1,2}),?\s+(\d{4})$")
_YEAR = re.compile(r"(?<!\d)(20\d{2})(?!\d)")


def _is_missing(value: Any) -> bool:
    if value is None:
        return True
    if isinstance(value, float) and math.isnan(value):
        return True
    return isinstance(value, str) and not value.strip()


def parse_plain_number(text: str) -> float | None:
    """'560,000' / '55.000' → 560000 / 55000; '45,000.0000' → 45000; '1.5' → 1.5."""
    text = text.strip().replace(" ", "")
    if not _PLAIN.match(text):
        return None
    has_dot, has_comma = "." in text, "," in text
    if has_dot and has_comma:
        decimal = "." if text.rfind(".") > text.rfind(",") else ","
        thousands = "," if decimal == "." else "."
        return float(text.replace(thousands, "").replace(decimal, "."))
    separator = "." if has_dot else "," if has_comma else ""
    if not separator:
        return float(text)
    head, *groups = text.split(separator)
    if groups and all(len(g) == 3 for g in groups) and head.lstrip("+-"):
        return float(head + "".join(groups))  # dấu phân cách nghìn
    if len(groups) == 1:
        return float(f"{head}.{groups[0]}")  # dấu thập phân
    return None


def parse_number(value: Any) -> float | None:  # noqa: PLR0911 — mỗi định dạng một nhánh
    """Số từ ô bất kỳ: tiền có đơn vị (tr/k/đ), số có phân cách nghìn, số kèm đơn vị tính."""
    if _is_missing(value) or isinstance(value, bool):
        return None
    if isinstance(value, (int, float)):
        return float(value)
    if not isinstance(value, str):
        return None
    text = _CURRENCY.sub("", value.strip().lower()).strip()
    if million := _MILLION.match(text):
        whole = float(million.group(1).replace(",", "."))
        tail = million.group(2)
        return whole * 1_000_000 + (float(tail) * 10 ** (6 - len(tail)) if tail else 0)
    if thousand := _THOUSAND.match(text):
        return float(thousand.group(1).replace(",", ".")) * 1000
    if (number := parse_plain_number(text)) is not None:
        return number
    if leading := _LEADING_NUMBER.match(text):  # "3 chai", "2 thùng"
        return parse_plain_number(leading.group(1))
    return None


def _safe_datetime(*parts: int) -> datetime | None:
    try:
        return datetime(*parts)  # type: ignore[arg-type]
    except ValueError:
        return None


def parse_datetime(  # noqa: PLR0911 — mỗi định dạng một nhánh
    value: Any, default_year: int | None = None
) -> datetime | None:
    """Ngày/giờ từ: datetime, số serial Excel, ISO, dd/mm/yyyy, '1 thg 6 2025', 'd/m' (cần năm)."""
    if _is_missing(value) or isinstance(value, bool):
        return None
    if isinstance(value, datetime):
        return value
    if isinstance(value, date):
        return datetime(value.year, value.month, value.day)
    if isinstance(value, (int, float)):
        low, high = _EXCEL_SERIAL_RANGE
        if low <= value <= high:
            moment = datetime.combine(_EXCEL_EPOCH, datetime.min.time())
            return moment + timedelta(days=float(value))
        return None
    if not isinstance(value, str):
        return None
    text = value.strip().lower()
    if iso := _ISO.match(text):
        return _safe_datetime(*(int(g) for g in iso.groups() if g is not None))
    if dmy := _DMY.match(text):
        day, month, year, *clock = dmy.groups()
        time_parts = [int(c) for c in clock if c is not None]
        return _safe_datetime(int(year), int(month), int(day), *time_parts)
    if vn := _VN_MONTH.match(text):
        return _safe_datetime(int(vn.group(3)), int(vn.group(2)), int(vn.group(1)))
    if (dm := _DM.match(text)) and default_year is not None:
        return _safe_datetime(default_year, int(dm.group(2)), int(dm.group(1)))
    if (number := parse_plain_number(text)) is not None and float(number).is_integer():
        return parse_datetime(number, default_year)
    return None


def year_in(text: str) -> int | None:
    """Năm 20xx xuất hiện trong tên sheet/file, dùng cho ngày không ghi năm (rulebook §8)."""
    match = _YEAR.search(text)
    return int(match.group(1)) if match else None
