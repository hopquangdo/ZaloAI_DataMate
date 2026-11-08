import pandas as pd

from datamate.modules.data.semantic import column_roles
from datamate.modules.data.semantic.propose import (
    BLANK_KEY,
    Proposal,
    accept,
    apply_roles,
    parse_proposals,
    render_tables,
)


def _tables() -> dict[str, pd.DataFrame]:
    n = 40
    orders = pd.DataFrame(
        {
            "Mã đơn hàng": [f"O{i}" for i in range(n)],
            "Ngày đặt hàng": pd.to_datetime(["2026-03-01"] * n),
            "Ghi chú": ["huỷ" if i % 8 == 0 else None for i in range(n)],
            "Zq": [f"x{i}" for i in range(n)],
        }
    )
    pay = pd.DataFrame(
        {
            "Ma don": [f"O{i}" for i in range(n)],
            "Ngay TT": ["2026-03-01 08:00:00"] * n,
            "So tien": [10000.0 + i for i in range(n)],
        }
    )
    return {"don": orders, "thu": pay}


def test_render_lists_only_unresolved_columns() -> None:
    text = render_tables(_tables())
    assert '"Ghi chú"' in text and '"Ngay TT"' in text and '"So tien"' in text
    assert '"Mã đơn hàng"' not in text  # đã có vai trò theo tên


def test_parse_reads_one_object_per_line_and_survives_truncation() -> None:
    reply = "\n".join(
        [
            "Kết quả:",
            '{"table": "don", "column": "Ghi chú", "role": "status", "blank_is": "hoan_thanh"}',
            '{"table": "don", "column": "Zq", "role": "không_có"}',
            '{"table": "ma", "column": "x", "role": "status"}',
            '{"table": "thu", "column": "So tien", "role": "receipt_amount", "blank_is": null}',
            '{"table": "thu", "column": "Ngay',  # bị cắt giữa chừng
        ]
    )
    got = parse_proposals(reply, _tables())
    assert got == {
        "don": {"Ghi chú": Proposal("status", "hoan_thanh")},
        "thu": {"So tien": Proposal("receipt_amount")},
    }


def test_accepted_roles_apply_and_change_dtypes() -> None:
    tables = _tables()
    proposals = {
        "don": {"Ghi chú": Proposal("status", "hoan_thanh")},
        "thu": {
            "Ngay TT": Proposal("receipt_date"),
            "So tien": Proposal("receipt_amount"),
        },
    }
    accepted = accept(tables, proposals)
    assert not accepted.rejected
    out = apply_roles(tables, accepted)
    assert pd.api.types.is_datetime64_any_dtype(out["thu"]["Ngay TT"])
    roles = {c: h.role for c, h in column_roles(out["thu"]).items()}
    assert roles["Ngay TT"] == "receipt_date" and roles["So tien"] == "receipt_amount"
    assert out["don"].attrs[BLANK_KEY] == {"Ghi chú": "hoan_thanh"}
    assert "Ngay TT" not in column_roles(tables["thu"])  # bảng gốc không bị sửa


def test_verification_rejects_values_that_do_not_fit_the_role() -> None:
    tables = _tables()
    proposals = {
        "don": {"Zq": Proposal("event_date")},  # chữ không đọc được thành ngày
        "thu": {"Ma don": Proposal("receipt_amount")},  # mã, không phải số
    }
    accepted = accept(tables, proposals)
    assert not accepted.roles and len(accepted.rejected) == 2


def test_llm_cannot_override_a_role_the_code_already_found() -> None:
    tables = _tables()
    assert "Ngày đặt hàng" in column_roles(tables["don"])
    accepted = accept(tables, {"don": {"Ngày đặt hàng": Proposal("created_at")}})
    assert not accepted.roles and "đã có vai trò" in accepted.rejected[0]


def test_order_id_in_a_flat_table_is_accepted_when_it_looks_like_ids() -> None:
    n = 60
    flat = pd.DataFrame(
        {
            "SoCT_k": [f"ORD{i // 3:05d}" for i in range(n)],  # mỗi đơn 3 dòng hàng
            "Hang": [f"Mặt hàng {i % 7}" for i in range(n)],
        }
    )
    tables = {"ban": flat}
    assert accept(tables, {"ban": {"SoCT_k": Proposal("order_id")}}).roles
    categories = pd.DataFrame({"Kenh": ["Quầy", "Zalo"] * (n // 2)})
    assert not accept({"ban": categories}, {"ban": {"Kenh": Proposal("order_id")}}).roles


def test_table_names_copied_from_readme_files_are_matched() -> None:
    tables = {"So_ban_hang": _tables()["don"]}
    reply = '{"table": "So_ban_hang_1.xlsx", "column": "Ghi chú", "role": "status"}'
    assert parse_proposals(reply, tables) == {"So_ban_hang": {"Ghi chú": Proposal("status")}}


def test_numeric_column_is_never_a_date() -> None:
    fee = pd.DataFrame({"Phí ship": [15000.0, 0.0, 20000.0, 15000.0, 0.0, 30000.0] * 4})
    accepted = accept({"ban": fee}, {"ban": {"Phí ship": Proposal("delivery_date")}})
    assert not accepted.roles and "không phải ngày" in accepted.rejected[0]


def test_channel_column_is_not_a_payment_method() -> None:
    n = 24
    channel = pd.DataFrame({"Kênh": ["Tại tiệm", "Zalo", "Sàn TMĐT"] * (n // 3)})
    got = accept({"ban": channel}, {"ban": {"Kênh": Proposal("payment")}})
    assert not got.roles
    methods = pd.DataFrame({"PTTT": ["Tiền mặt", "Chuyển khoản", "Ví điện tử"] * (n // 3)})
    assert accept({"ban": methods}, {"ban": {"PTTT": Proposal("payment")}}).roles


def test_rare_roles_are_not_proposable() -> None:
    reply = '{"table": "don", "column": "Zq", "role": "active_ingredient"}'
    assert parse_proposals(reply, _tables()) == {}
