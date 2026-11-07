"""Doanh nghiệp ghi những loại thông tin nào, và dữ liệu giao dịch trải từ ngày nào đến ngày nào.

Dùng cho luật "không trả lời được" (rulebook §7): kỳ nằm hoàn toàn ngoài khoảng có dữ liệu, hoặc
shop không ghi loại thông tin câu hỏi cần thì đáp án là unanswerable, không phải 0.
Chỉ dựa vào tên cột (qua gợi ý vai trò) và việc cột có giá trị hay không.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from datetime import date

import pandas as pd

from datamate.core.text import fold
from datamate.modules.data.ingestion import SOURCE_COLUMN, Business
from datamate.modules.data.semantic.roles import _split_camel, column_roles

# loại thông tin -> mẫu tên cột (đã bỏ dấu) chứng tỏ shop có ghi loại đó
_NAME_PATTERNS: dict[str, str] = {
    "stock": r"\bton\b(?!.*\b(lon nhat|nho nhat|toi thieu|toi da)\b)",
    "gender": r"gioi tinh|\bnam ?nu\b|\bgender\b",
    "address": r"dia chi|\baddr|khu vuc|duong\b",
    "channel": r"\bkenh\b|ban qua|nguon don|\bchannel\b|loai ban",
}
# loại thông tin -> mẫu giá trị (đã bỏ dấu) trong cột chữ, khi tên cột không nói lên được
_VALUE_PATTERNS: dict[str, str] = {
    "channel": r"\b(phone|zalo|facebook|shopee|tiktok|online|dien thoai|tai quay|grab)\b",
}
# loại thông tin -> vai trò cột (xem column_roles.tsv)
_ROLE_CAPS: dict[str, set[str]] = {
    "customer": {"customer", "customer_code"},
    "customer_group": {"customer_group"},
    "staff": {"staff", "staff_code"},
    "payment": {"payment"},
    "debt": {"debt", "paid_amount", "due_date", "receipt_amount"},
    "import": {"import_id", "import_price", "qty_imported", "import_amount", "import_date"},
    "expiry": {"expiry_date", "lot_id"},
    "cost": {"cost_price"},
    "status": {"status"},
}


@dataclass(frozen=True)
class Capabilities:
    has: frozenset[str]
    data_start: date | None = None  # ngày giao dịch sớm nhất của bảng giao dịch chính
    data_end: date | None = None
    has_time_of_day: bool = False
    roles: dict[str, set[str]] = field(default_factory=dict)  # vai trò -> các cột "bảng.cột"


def _transaction_dates(business: Business) -> tuple[date | None, date | None, bool]:
    """Khoảng ngày của bảng giao dịch lớn nhất (bảng có mã đơn và ngày phát sinh)."""
    best: tuple[int, pd.Series] | None = None
    for table in business.tables.values():
        hints = column_roles(table)
        roles = {h.role for h in hints.values()}
        if "order_id" not in roles:
            continue
        dates = [c for c, h in hints.items() if h.role == "event_date"]
        for column in dates:
            series = table[column].dropna()
            if not series.empty and (best is None or len(series) > best[0]):
                best = (len(series), series)
    if best is None:
        return None, None, False
    series = best[1]
    has_time = bool((series.dt.normalize() != series).any())
    return series.min().date(), series.max().date(), has_time


def capabilities(business: Business) -> Capabilities:
    has: set[str] = set()
    roles: dict[str, set[str]] = {}
    for name, table in business.tables.items():
        for column, hint in column_roles(table).items():
            if table[column].notna().any():
                roles.setdefault(hint.role, set()).add(f"{name}.{column}")
        for column in table.columns:
            if column == SOURCE_COLUMN or not table[column].notna().any():
                continue
            key = " ".join(re.findall(r"[a-z0-9]+", fold(_split_camel(str(column)))))
            has.update(cap for cap, pattern in _NAME_PATTERNS.items() if re.search(pattern, key))
            if pd.api.types.is_numeric_dtype(table[column]):
                continue
            values = table[column].dropna().astype(str).unique()[:50]
            sample = " ".join(fold(v).replace("_", " ") for v in values)
            has.update(
                cap for cap, pattern in _VALUE_PATTERNS.items() if re.search(pattern, sample)
            )
    for cap, wanted in _ROLE_CAPS.items():
        if wanted & roles.keys():
            has.add(cap)
    if "import" in has:  # tồn kho tính được từ nhập trừ bán dù không có bảng tồn
        has.add("stock")
    start, end, has_time = _transaction_dates(business)
    return Capabilities(frozenset(has), start, end, has_time, roles)
