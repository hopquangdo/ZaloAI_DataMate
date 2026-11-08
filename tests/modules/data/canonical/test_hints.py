import pandas as pd

from datamate.modules.data.canonical.hints import error_hint, missing_column_hint, sql_shape_hint

TABLES = {
    "don_tinh_doanh_thu": pd.DataFrame({"Mã đơn": [1], "Doanh thu đơn": [2.0]}),
    "dong_hang_tinh_doanh_thu": pd.DataFrame({"Mã đơn": [1], "Tên hàng": ["a"]}),
}


def test_missing_column_names_the_tables_that_have_it() -> None:
    text = missing_column_hint("Tên hàng", TABLES)
    assert "dong_hang_tinh_doanh_thu" in text and "KHÔNG có cột về hàng" in text
    assert missing_column_hint("Cột lạ", TABLES) == ""


def test_error_hints_cover_the_common_failures() -> None:
    assert "Thiếu ngoặc" in error_hint("TypeError: Cannot perform 'rand_' with a dtyped [bool]")
    assert "cột ngày" in error_hint("TypeError: 'DatetimeArray' with dtype datetime64[us] does not support operation 'sum'")
    assert "chưa được gán" in error_hint("NameError: name 'd' is not defined")
    assert error_hint("ValueError: whatever") == ""


def test_sql_shape_hint_only_for_one_column_many_rows() -> None:
    assert "COUNT(*)" in sql_shape_hint(25, 1)
    assert sql_shape_hint(1, 2) == ""
