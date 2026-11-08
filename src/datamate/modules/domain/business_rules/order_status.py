"""Phân loại trạng thái đơn hàng viết tự do thành nhãn chuẩn (rulebook §6)."""

from __future__ import annotations

import pandas as pd

from datamate.core.text import fold

# Thứ tự quan trọng: "huỷ" và "trả hàng" xét trước, "hoàn thành" xét sau
# (vì "hoàn hàng" ≠ "hoàn thành").
_STATUS_RULES: tuple[tuple[str, tuple[str, ...]], ...] = (
    ("huy", ("huy", "cancel", "cancelled", "canceled", "khong giao duoc", "giao khong thanh",
             "that bai", "failed")),
    ("tra_hang", ("hoan hang", "tra hang", "tra lai", "hoan tra", "doi tra", "hang tra ve",
                  "return", "returned", "refund", "refunded")),
    ("dang_giao", ("dang giao", "dang gui", "dang van chuyen", "dang xu ly", "cho giao",
                   "shipping", "shipped", "delivering", "pending")),
    ("hoan_thanh", ("hoan thanh", "da giao", "da lay", "da xong", "xong", "thanh cong", "ok",
                    "completed", "complete", "done", "delivered", "success")),
)


def classify_status(value: object) -> str:
    """Trạng thái đơn → 'hoan_thanh' | 'huy' | 'tra_hang' | 'dang_giao' | 'khac'."""
    if not isinstance(value, str):
        return "khac"
    text = f" {fold(value).strip()} "  # so khớp theo từ nguyên vẹn: "chuyen" không chứa "huy"
    for label, keywords in _STATUS_RULES:
        if any(f" {k} " in text for k in keywords):
            return label
    return "khac"


def order_status(column: pd.Series) -> pd.Series:
    """Áp classify_status cho cả cột trạng thái."""
    return column.map(classify_status)
