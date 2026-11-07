import numpy as np
import pandas as pd

from datamate.modules.data.ingestion.columns import column_words, type_columns
from datamate.modules.data.ingestion.grouping import fill_group_cells
from datamate.modules.data.ingestion.header import apply_header


def test_column_words_splits_camel_case_but_not_vietnamese() -> None:
    assert column_words("ThoiGianLap") == "thoi gian lap"
    assert column_words("Mã đơn hàng") == "ma don hang"
    assert column_words("so_luong") == "so luong"


def test_header_skips_title_and_filter_rows() -> None:
    raw = pd.DataFrame(
        [
            ["SỔ CHI TIẾT BÁN HÀNG", None, None],
            [None, None, None],
            ["Mã đơn hàng", "Ngày", "Thành tiền"],
            ["ORD1", "01/04/2025", "45,000"],
        ]
    )
    table = apply_header(raw)
    assert list(table.columns) == ["Mã đơn hàng", "Ngày", "Thành tiền"]
    assert len(table) == 1


def test_two_level_header_uses_the_fuller_row() -> None:
    raw = pd.DataFrame(
        [["Hàng", None, "Tiền"], ["Hàng", "so_luong", "Trị giá"], ["Cà phê", "1", "25.000đ"]]
    )
    assert list(apply_header(raw).columns) == ["Hàng", "so_luong", "Trị giá"]


def test_type_columns_parses_money_dates_and_keeps_phone_as_text() -> None:
    table = pd.DataFrame(
        {
            "Ngày lập": ["1/1", "01/02/2025", "45689"],
            "Tiền": ["1tr440", "55.000đ", "396k"],
            "Điện thoại": ["0901234567", "0912345678", None],
        }
    )
    typed = type_columns(table, default_year=pd.Series([2025, 2025, 2025]))
    assert typed["Ngày lập"].dt.strftime("%Y-%m-%d").tolist() == [
        "2025-01-01",
        "2025-02-01",
        "2025-02-01",
    ]
    assert typed["Tiền"].tolist() == [1_440_000, 55_000, 396_000]
    assert typed["Điện thoại"].iloc[0] == "0901234567"


def test_fill_group_cells_fills_order_level_columns_only() -> None:
    table = pd.DataFrame(
        {
            "Mã đơn hàng": ["ORD1", None, "ORD2"],
            "Khách": ["An", None, "Bình"],
            "Tên sản phẩm": ["A", "B", "C"],
            "Ghi chú": [None, None, "x"],
        }
    )
    filled, columns = fill_group_cells(table)
    assert columns == ["Mã đơn hàng", "Khách"]
    assert filled["Mã đơn hàng"].tolist() == ["ORD1", "ORD1", "ORD2"]
    assert filled["Khách"].tolist() == ["An", "An", "Bình"]
    assert filled["Ghi chú"].isna().tolist() == [True, True, False]
    assert not np.any(filled["Tên sản phẩm"].isna())
