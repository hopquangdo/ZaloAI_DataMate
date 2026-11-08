"""Gợi ý sửa lỗi cho bộ giải, dựa trên bảng chuẩn tắc: biến thông báo lỗi thô thành chỉ dẫn cụ thể.

Các lỗi lặp lại nhiều nhất của model nhỏ (xem nhật ký chạy): gọi cột không có ở bảng đang dùng
(nhưng có ở bảng khác), quên ngoặc quanh điều kiện khi dùng ``&`` / ``|``, cộng cột ngày, dùng biến
chưa gán, truy vấn trả nhiều dòng cho câu "có bao nhiêu nhóm". Mỗi gợi ý chỉ dựa vào chính thông báo
lỗi và danh sách bảng, không đoán đáp án.
"""

from __future__ import annotations

import re
from collections.abc import Mapping

import pandas as pd

from datamate.modules.data.canonical.build import LINES, ORDERS, VIEW_LINES, VIEW_ORDERS

_ORDER_TABLES = (ORDERS, VIEW_ORDERS)
_LINE_TABLES = (LINES, VIEW_LINES)


def tables_having(column: str, tables: Mapping[str, pd.DataFrame]) -> list[str]:
    """Tên các bảng có đúng cột ``column``."""
    return [name for name, table in tables.items() if column in map(str, table.columns)]


def missing_column_hint(column: str, tables: Mapping[str, pd.DataFrame]) -> str:
    """Cột không có ở bảng đang dùng: nói cột đó có ở bảng nào."""
    owners = tables_having(column, tables)
    if not owners:
        return ""
    text = f"\nCột '{column}' CÓ ở bảng: " + ", ".join(f'"{name}"' for name in owners) + "."
    if any(name in _LINE_TABLES for name in owners) and not any(
        name in _ORDER_TABLES for name in owners
    ):
        text += (
            " Bảng đơn (don_*) KHÔNG có cột về hàng: muốn lọc theo mặt hàng / nhóm hàng phải dùng "
            'bảng dòng hàng (dong_hang_*) và đếm đơn bằng số "Mã đơn" khác nhau.'
        )
    return text


def error_hint(message: str) -> str:
    """Gợi ý cho các lỗi thực thi pandas hay gặp; chuỗi rỗng nếu không nhận ra."""
    if re.search(r"'(rand_|ror_|rxor|and_|or_|xor)'|dtyped \[bool\]", message):
        return (
            "\nThiếu ngoặc: khi ghép điều kiện bằng & hoặc | phải bọc từng điều kiện, vd. "
            '(d["A"] == x) & (d["B"] > y) & P.month(2026, 3).contains(d["Ngày đặt"]).'
        )
    if re.search(r"(Datetime\w*|datetime64\w*)[^\n]*(sum|mean)'", message):
        return "\nKhông cộng được cột ngày. Cộng cột tiền / số lượng; nhóm theo ngày bằng .dt.date."
    name = re.search(r"NameError: name '(\w+)' is not defined", message)
    if name:
        return (
            f"\nBiến '{name.group(1)}' chưa được gán trong đoạn code này. Mỗi lần trả lời phải tự "
            'viết lại từ đầu, vd. d = T["don_tinh_doanh_thu"].'
        )
    if "'int' object has no attribute 'contains'" in message:
        return "\nP.xxx(...) phải trả về kỳ (Period); dùng P.month(y, m) / P.between(đầu, cuối)."
    return ""


def sql_shape_hint(rows: int, columns: int) -> str:
    """Truy vấn trả nhiều dòng cho kiểu một giá trị: thường là thiếu COUNT / tổng bao ngoài."""
    if columns == 1 and rows > 1:
        return (
            f" Truy vấn đang trả {rows} dòng (mỗi nhóm một dòng). Nếu câu hỏi hỏi 'có bao nhiêu' "
            "khách / mặt hàng / ngày thì bọc lại: SELECT COUNT(*) FROM (<truy vấn của bạn>)."
        )
    return ""
