"""Hàm nghiệp vụ đăng ký vào DuckDB để câu SQL của LLM gọi như hàm thường.

Cùng luật với bộ giải pandas (lấy từ ``domain``), để hai bộ giải không lệch nhau về định nghĩa.
"""

from __future__ import annotations

from typing import Any

from duckdb import DuckDBPyConnection
from duckdb.sqltypes import BIGINT, DOUBLE, VARCHAR

from datamate.core.text import name_key, normalize_text
from datamate.modules.domain.business_rules import classify_status, round_money


def _text(fn: Any) -> Any:
    def call(value: Any) -> Any:
        return None if value is None else fn(str(value))

    return call


def register_functions(connection: DuckDBPyConnection) -> None:
    connection.create_function("fold", _text(name_key), [VARCHAR], VARCHAR)
    connection.create_function("norm", _text(normalize_text), [VARCHAR], VARCHAR)
    connection.create_function("order_status", _text(classify_status), [VARCHAR], VARCHAR)
    connection.create_function(
        "round_money", lambda x: None if x is None else round_money(float(x)), [DOUBLE], BIGINT
    )


FUNCTIONS_DOC = """\
- order_status(cột_trạng_thái) → 'hoan_thanh' | 'huy' | 'tra_hang' | 'dang_giao' | 'khac'.
  LUÔN dùng để lọc đơn; đơn tính doanh thu = order_status(...) IN ('hoan_thanh', 'dang_giao').
- fold(s): chữ thường, bỏ dấu và dấu câu / ngoặc, để so tên: fold("Tên hàng") = fold('ca phe m').
- norm(s): chuẩn hoá như bộ chấm (giữ dấu).
- round_money(x): làm tròn tiền về đồng, nửa lên."""
