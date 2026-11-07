import pandas as pd

from datamate.modules.domain.business_rules import classify_status, order_status


def test_order_status_classification() -> None:
    raw = [
        "Đã hoàn thành",
        "Đã hủy",
        "Hủy đơn",
        "Đã hoàn hàng",
        "Hàng trả về",
        "Đang giao dịch",
        "Đang vận chuyển",
        "xong",
        "Thành công",
        "Cancel",
        "Không giao được",
        None,
    ]
    expected = [
        "hoan_thanh",
        "huy",
        "huy",
        "tra_hang",
        "tra_hang",
        "dang_giao",
        "dang_giao",
        "hoan_thanh",
        "hoan_thanh",
        "huy",
        "khac",
        "khac",
    ]
    assert order_status(pd.Series(raw)).tolist() == expected


def test_whole_words_only() -> None:
    assert classify_status("chuyển khoản") == "khac"  # "chuyen" không chứa "huy"
