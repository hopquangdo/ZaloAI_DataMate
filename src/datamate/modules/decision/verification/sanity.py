"""Kiểm tra hợp lý một đáp án trước khi tính phiếu (không gọi LLM).

Đáp án bị loại thì coi như lần sinh đó không trả lời (abstain), để không bị −1 vì một lỗi dễ thấy.
Chỉ giữ luật không loại nhầm đáp án chuẩn nào của train (xem scripts/check_sanity.py).
"""

from __future__ import annotations

import math

import pandas as pd

from datamate.core.text import normalize_text
from datamate.modules.data.ingestion import SOURCE_COLUMN, Business
from datamate.modules.domain.answer import Answer, AnswerType

_WEEKDAYS = frozenset(
    normalize_text(name)
    for name in ("Thứ Hai", "Thứ Ba", "Thứ Tư", "Thứ Năm", "Thứ Sáu", "Thứ Bảy", "Chủ Nhật")
) | frozenset(normalize_text(f"Thứ {n}") for n in range(2, 8))
_MAX_PERCENT = 100_000.0


def known_names(business: Business) -> frozenset[str]:
    """Mọi giá trị chữ (đã chuẩn hoá như bộ chấm) có trong dữ liệu của doanh nghiệp."""
    names: set[str] = set()
    for table in business.tables.values():
        for column in table.columns:
            if column == SOURCE_COLUMN or pd.api.types.is_numeric_dtype(table[column]):
                continue
            if pd.api.types.is_datetime64_any_dtype(table[column]):
                continue
            names.update(normalize_text(str(v)) for v in table[column].dropna().unique())
    return frozenset(names)


def _name_ok(value: object, names: frozenset[str]) -> bool:
    if not isinstance(value, str):
        return True
    key = normalize_text(value)
    if key in names or key in _WEEKDAYS:
        return True
    # giá trị có thể kèm thông tin khác: "Cao Long Minh (0321806537)" chứa "cao long minh"
    padded = f" {key} "
    return any(padded in f" {name} " for name in names)


def check_answer(answer: Answer, names: frozenset[str]) -> str | None:
    """Lý do loại đáp án, hoặc None nếu đáp án qua được kiểm tra."""
    if not answer.has_value:
        return None
    value = answer.value
    if answer.type is AnswerType.STRING and not _name_ok(value, names):
        return f"tên {value!r} không có trong dữ liệu"
    if answer.type is AnswerType.LIST and isinstance(value, tuple):
        missing = [v for v in value if not _name_ok(v, names)]
        if missing:
            return f"các tên không có trong dữ liệu: {missing[:3]!r}"
    if answer.type in (AnswerType.NUMBER, AnswerType.PERCENT) and isinstance(value, (int, float)):
        if isinstance(value, float) and not math.isfinite(value):
            return "giá trị không hữu hạn"
        if answer.type is AnswerType.PERCENT and abs(value) > _MAX_PERCENT:
            return f"phần trăm bất thường: {value}"
    return None
