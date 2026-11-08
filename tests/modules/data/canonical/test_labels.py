import pandas as pd

from datamate.modules.data.canonical import (
    ORDERS,
    build_canonical,
    cached_labels,
    parse_labels,
    unknown_status_values,
)


def test_parse_labels_keeps_only_known_values_and_the_four_labels() -> None:
    text = 'Kết quả: {"Bom hàng": "huy", "Lạ": "khac", "khác hẳn": "huy"}'
    assert parse_labels(text, ["Bom hàng", "Lạ"]) == {"Bom hàng": "huy"}
    assert parse_labels("không có json", ["x"]) == {}


def test_cached_labels_asks_only_for_new_values(tmp_path) -> None:
    calls: list[list[str]] = []

    def labeler(values: list[str]) -> dict[str, str]:
        calls.append(values)
        return dict.fromkeys(values, "huy")

    path = tmp_path / "biz.json"
    assert cached_labels(path, ["A"], labeler) == {"A": "huy"}
    assert cached_labels(path, ["A", "B"], labeler) == {"A": "huy", "B": "huy"}
    assert calls == [["A"], ["B"]]


def test_unknown_status_values_feed_the_builder() -> None:
    n = 30
    tables = {
        "don": pd.DataFrame(
            {
                "Mã đơn hàng": [f"O{i}" for i in range(n)],
                "Ngày đặt hàng": pd.to_datetime(["2026-03-01"] * n),
                "Trạng thái đơn hàng": ["Đã giao"] * (n - 1) + ["Bom hàng"],
                "Tên sản phẩm": ["Trà"] * n,
                "Số lượng sản phẩm": [1.0] * n,
                "Tổng tiền": [10000.0] * n,
            }
        )
    }
    assert unknown_status_values(tables) == ["Bom hàng"]
    orders = build_canonical(tables, labels={"Bom hàng": "huy"}).tables[ORDERS]
    assert (orders["Trạng thái chuẩn"] == "huy").sum() == 1
