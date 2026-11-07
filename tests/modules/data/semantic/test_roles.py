"""Gợi ý vai trò cột: các ca dễ làm mất nghĩa đã gặp trên dữ liệu thật."""

import pandas as pd
import pytest

from datamate.modules.data.semantic import classify, column_roles


def role(column: str) -> str | None:
    rule = classify(column)
    return None if rule is None or rule.role == "-" else rule.role


@pytest.mark.parametrize(
    ("column", "expected"),
    [
        # bỏ dấu không được làm lẫn từ
        ("Hàng", "product"),
        ("Hãng", None),  # thương hiệu
        ("Hạng", None),  # hạng khách
        ("Tiến độ", None),
        # "hàng" trong cụm ghép không phải hàng hoá
        ("Mã khách hàng", "customer_code"),
        ("Mã đơn hàng", "order_id"),
        ("Mã nhập hàng", "import_id"),
        ("Nhóm hàng", "category"),
        ("Loại khách", "customer_group"),
        # từ bổ nghĩa tạo vai trò riêng
        ("Số lượng trả", "qty_returned"),
        ("Số lượng quy đổi", "qty_base"),
        ("SLQuyDoi", "qty_base"),
        ("Giá vốn", "cost_price"),
        ("GiaVonLucBan", "cost_price"),
        ("Tổng điểm", "points"),
        ("Khách đã trả", "paid_amount"),
        ("Tiền hàng trước giảm", "order_subtotal"),
        ("Tổng sau giảm giá", "order_total"),
        ("Ngày sinh", "birth_date"),
        ("Ngày giao dịch", "event_date"),
        ("NgayGioPhatSinh", "event_date"),
        ("Hạn sử dụng", "expiry_date"),
        # hai kiểu bỏ dấu thanh
        ("Mã hóa đơn", "order_id"),
        ("Mã hoá đơn", "order_id"),
        # mơ hồ thì không gợi ý
        ("TT dòng", None),
        ("Ngày TT", None),
        ("Mã thanh toán", None),
        ("SoHoaDonDienTu", None),
    ],
)
def test_classify(column: str, expected: str | None) -> None:
    assert role(column) == expected


def _lines(n: int = 40) -> pd.DataFrame:
    qty = pd.Series(range(1, n + 1), dtype=float)
    price = pd.Series([1000.0] * n)
    return pd.DataFrame(
        {"Mã hóa đơn": [f"HD{i}" for i in range(n)], "Số lượng": qty, "Đơn giá": price,
         "Thành tiền": qty * price, "Trạng thái": ["xong"] * n}
    )


def test_amount_gets_evidence_when_it_equals_qty_times_price() -> None:
    hints = column_roles(_lines())
    assert "≈ số lượng × đơn giá" in hints["Thành tiền"].label
    assert hints["Trạng thái"].role == "status"


def test_wrong_value_kind_drops_the_hint() -> None:
    table = pd.DataFrame({"Thành tiền": ["a", "b"], "Ngày": [1, 2]})
    assert column_roles(table) == {}


def test_status_outside_an_order_table_is_not_hinted() -> None:
    table = pd.DataFrame({"Tên khách hàng": ["An"], "Trạng thái": ["Đang hoạt động"]})
    assert "Trạng thái" not in column_roles(table)


def test_import_table_reinterprets_generic_columns() -> None:
    table = pd.DataFrame(
        {"Mã nhập hàng": ["PN1"], "Mã hàng": ["SP1"], "Số lượng": [5.0], "Đơn giá": [100.0]}
    )
    hints = column_roles(table)
    assert hints["Đơn giá"].role == "import_price"
    assert hints["Số lượng"].role == "qty_imported"
