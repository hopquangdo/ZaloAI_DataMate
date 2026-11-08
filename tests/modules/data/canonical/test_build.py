import pandas as pd

from datamate.modules.data.canonical import LINES, ORDERS, build_canonical
from datamate.modules.domain.business_rules import classify_status


def _header(n: int = 30) -> pd.DataFrame:
    return pd.DataFrame(
        {
            "Mã hóa đơn": [f"ORD{i:03d}" for i in range(n)],
            "Thời gian": pd.to_datetime("2026-03-01") + pd.to_timedelta(range(n), unit="D"),
            "Trạng thái": ["completed"] * (n - 2) + ["cancelled", "returned"],
            "Tổng tiền hàng": [30000.0] * n,
            "Tổng sau giảm giá": [29000.0] * n,
        }
    )


def _detail(n: int = 30) -> pd.DataFrame:
    rows = []
    for i in range(n):
        rows.append((f"ORD{i:03d}", "Cà phê", 2.0, 10000.0, 20000.0, 2.0, 1))
        rows.append((f"ORD{i:03d}", "Trà", 1.0, 10000.0, 10000.0, 1.0, 2))
    frame = pd.DataFrame(
        rows,
        columns=["Mã hóa đơn", "Tên hàng", "Số lượng", "Đơn giá", "Thành tiền",
                 "Số lượng quy đổi", "STT"],
    )
    return pd.concat([frame, frame.iloc[[0]]], ignore_index=True)  # một dòng lặp nguyên văn


def test_revenue_uses_line_sum_and_drops_duplicate_lines() -> None:
    canon = build_canonical({"DanhSachHoaDon": _header(), "DanhSachHoaDonChiTiet": _detail()})
    orders = canon.tables[ORDERS]
    assert set(orders.columns) >= {"Mã đơn", "Ngày đặt", "Trạng thái chuẩn", "Doanh thu đơn"}
    assert orders.loc[orders["Mã đơn"] == "ORD000", "Doanh thu đơn"].item() == 30000.0
    assert len(canon.tables[LINES]) == 60


def test_english_status_labels_and_cancelled_orders_do_not_count() -> None:
    orders = build_canonical({"hd": _header(), "ct": _detail()}).tables[ORDERS]
    assert int(orders["Tính vào doanh thu"].sum()) == 28
    assert (orders["Trạng thái chuẩn"] == "huy").sum() == 1
    assert (orders["Trạng thái chuẩn"] == "tra_hang").sum() == 1


def test_order_with_a_return_slip_is_void_even_if_status_says_completed() -> None:
    returns = pd.DataFrame({"Mã phiếu trả": ["TH1"], "Mã hóa đơn": ["ORD005"]})
    tables = {"hd": _header(), "ct": _detail(), "tra": returns}
    orders = build_canonical(tables).tables[ORDERS]
    assert not orders.loc[orders["Mã đơn"] == "ORD005", "Tính vào doanh thu"].item()


def test_sales_book_without_order_ids_keeps_every_line() -> None:
    book = pd.DataFrame(
        {
            "ngay_ban": pd.to_datetime(["2026-03-01"] * 25),
            "Nội dung": ["Cà phê"] * 25,
            "Số lượng": [1.0] * 25,
            "don_gia": [10000.0] * 25,
            "Tổng tiền": [10000.0] * 25,
        }
    )
    canon = build_canonical({"SoBanHang": book})
    assert ORDERS not in canon.tables
    assert len(canon.tables[LINES]) == 25  # dòng giống nhau của bảng không ghi theo đơn vẫn tính


def test_unrecognised_layout_builds_nothing() -> None:
    assert build_canonical({"x": pd.DataFrame({"a": [1, 2]})}).tables == {}


def test_status_words_seen_in_other_shops() -> None:
    assert classify_status("completed") == "hoan_thanh"
    assert classify_status("cancelled") == "huy"
    assert classify_status("khách hủy") == "huy"
    assert classify_status("Chờ giao") == "dang_giao"
    assert classify_status("Hoàn trả") == "tra_hang"


def test_canonical_carries_extra_columns_and_replaces_source() -> None:
    n = 30
    flat = pd.DataFrame(
        {
            "Mã đơn hàng": [f"O{i // 2}" for i in range(n)],
            "Ngày đặt hàng": pd.to_datetime(["2026-03-01"] * n),
            "Trạng thái đơn hàng": ["Đã giao"] * n,
            "Tên sản phẩm": [f"Hàng {i % 3}" for i in range(n)],
            "Số lượng sản phẩm": [1.0] * n,
            "Tổng tiền": [10000.0] * n,
            "Kênh": ["Zalo" if i // 2 < 8 else "Quầy" for i in range(n)],
            "Ghi chú dòng": [f"g{i}" for i in range(n)],
        }
    )
    canon = build_canonical({"ban": flat})
    assert canon.replaces == ("ban",)
    orders, lines = canon.tables["don_chuan"], canon.tables["dong_hang_chuan"]
    assert "Kênh" in orders.columns  # không đổi trong một đơn → thuộc tính của đơn
    assert "Ghi chú dòng" not in orders.columns  # đổi theo dòng → chỉ ở bảng dòng hàng
    assert {"Kênh", "Ghi chú dòng"} <= set(lines.columns)
    assert "Trạng thái đơn hàng" not in lines.columns  # đã có trạng thái chuẩn


def _debt_tables() -> dict[str, pd.DataFrame]:
    n = 30
    orders = pd.DataFrame(
        {
            "Mã đơn hàng": [f"O{i}" for i in range(n)],
            "Ngày đặt hàng": pd.to_datetime(["2026-03-01"] * n),
            "Trạng thái đơn hàng": ["Đã giao"] * n,
            "Tên sản phẩm": ["Trà"] * n,
            "Số lượng sản phẩm": [2.0] * n,
            "Giá vốn": [3000.0] * n,
            "Tổng tiền": [10000.0] * n,
            "Phương thức thanh toán": ["Ghi nợ"] * 5 + ["Tiền mặt"] * (n - 5),
        }
    )
    receipts = pd.DataFrame(
        {
            "Mã phiếu thu": [f"R{i}" for i in range(n + 2)],
            "Mã đơn hàng": [f"O{i}" for i in range(n)] + ["O0", "O1"],
            "Ngày thu": pd.to_datetime(["2026-03-01"] * n + ["2026-03-10", "2026-04-02"]),
            "Số tiền thu": [4000.0] * 5 + [10000.0] * (n - 5) + [6000.0, 6000.0],
        }
    )
    return {"don": orders, "thu": receipts}


def test_payments_table_defines_debt_repayment() -> None:
    canon = build_canonical(_debt_tables())
    assert "thu" in canon.replaces
    pay = canon.tables["thanh_toan_chuan"]
    repaid = pay[pay["Là trả nợ"]]
    assert repaid["Số tiền thu"].sum() == 12000.0  # chỉ khoản thu SAU ngày mua của đơn ghi nợ
    orders = canon.tables["don_chuan"]
    assert orders["Nợ thêm"].sum() == 5 * 6000.0  # đơn ghi nợ: 10000 - 4000 trả ngay


def test_line_profit_uses_cost_on_the_line() -> None:
    lines = build_canonical(_debt_tables()).tables["dong_hang_chuan"]
    assert lines["Lãi gộp dòng"].iloc[0] == 10000.0 - 2.0 * 3000.0


def test_product_names_and_groups_come_from_catalog_by_code() -> None:
    n = 30
    codes = [f"SP{i % 3}" for i in range(n)]
    sales = pd.DataFrame(
        {
            "Mã đơn hàng": [f"O{i}" for i in range(n)],
            "Ngày đặt hàng": pd.to_datetime(["2026-03-01"] * n),
            "Trạng thái đơn hàng": ["Đã giao"] * n,
            "Mã sản phẩm": codes,
            "Số lượng sản phẩm": [1.0] * n,
            "Tổng tiền": [10000.0] * n,
        }
    )
    catalog = pd.DataFrame(
        {
            "Mã sản phẩm": ["SP0", "SP1", "SP2"],
            "Mô tả": ["Trà đào cam sả", "Sữa tươi ít đường", "Bánh mì que cay"],
            "Loại hàng hóa": ["Trà", "Sữa", "Bánh"],
        }
    )
    canon = build_canonical({"ban": sales, "dm": catalog})
    lines = canon.tables["dong_hang_chuan"]
    assert set(lines["Tên hàng"]) == {"Trà đào cam sả", "Sữa tươi ít đường", "Bánh mì que cay"}
    assert set(lines["Loại hàng hóa"]) == {"Trà", "Sữa", "Bánh"}


def test_ledger_rows_become_orders() -> None:
    n = 25
    ledger = pd.DataFrame(
        {
            "Ngày": pd.to_datetime(["2026-03-01"] * n),
            "Xe": [f"wave {i}" for i in range(n)],
            "Tiền": [100000.0] * n,
            "Thợ": ["Đức"] * n,
        }
    )
    canon = build_canonical({"sổ": ledger})
    orders = canon.tables["don_chuan"]
    assert len(orders) == n and orders["Doanh thu đơn"].sum() == n * 100000.0
    assert {"Xe", "Thợ"} <= set(orders.columns)
    assert len(canon.tables["don_tinh_doanh_thu"]) == n


def test_product_code_column_is_found_by_values() -> None:
    n = 30
    sales = pd.DataFrame(
        {
            "Mã đơn hàng": [f"O{i}" for i in range(n)],
            "Ngày đặt hàng": pd.to_datetime(["2026-03-01"] * n),
            "Trạng thái đơn hàng": ["Đã giao"] * n,
            "Zxy": [f"SP{i % 3}" for i in range(n)],  # tên cột không nhận ra
            "Số lượng sản phẩm": [1.0] * n,
            "Tổng tiền": [10000.0] * n,
        }
    )
    catalog = pd.DataFrame(
        {"Mã": ["SP0", "SP1", "SP2"], "Mô tả": ["Trà đào cam", "Sữa tươi tiệt trùng", "Bánh mì que"]}
    )
    lines = build_canonical({"ban": sales, "dm": catalog}).tables["dong_hang_chuan"]
    assert set(lines["Tên hàng"]) == {"Trà đào cam", "Sữa tươi tiệt trùng", "Bánh mì que"}


def test_walk_in_customers_have_no_identity() -> None:
    n = 30
    sales = pd.DataFrame(
        {
            "Mã đơn hàng": [f"O{i}" for i in range(n)],
            "Ngày đặt hàng": pd.to_datetime(["2026-03-01"] * n),
            "Trạng thái đơn hàng": ["Đã giao"] * n,
            "Tên khách hàng": ["Khách lẻ"] * 10 + ["Lê Văn A"] * 10 + ["lê văn a"] * 5 + [None] * 5,
            "Tên sản phẩm": ["Trà"] * n,
            "Số lượng sản phẩm": [1.0] * n,
            "Tổng tiền": [10000.0] * n,
        }
    )
    orders = build_canonical({"ban": sales}).tables["don_chuan"]
    ident = orders["Khách định danh"]
    assert ident.isna().sum() == 15  # khách lẻ + đơn không tên
    assert ident.dropna().nunique() == 1  # "Lê Văn A" và "lê văn a" là một khách
