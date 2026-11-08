from datamate.modules.solvers.view_misuse import ViewMisuseCheck


def _state(code: str, warned: list[str] | None = None) -> dict:
    return {"code": code, "warned": warned or []}


def test_cancel_filter_on_filtered_view_is_flagged_once() -> None:
    check = ViewMisuseCheck()
    sql = "SELECT COUNT(*) FROM \"don_tinh_doanh_thu\" WHERE \"Trạng thái chuẩn\" = 'huy'"
    got = check(_state(sql))  # type: ignore[arg-type]
    assert got is not None and got.rejected
    assert check(_state(sql, got.names)) is None  # type: ignore[arg-type]


def test_full_table_or_plain_revenue_is_fine() -> None:
    check = ViewMisuseCheck()
    full = "d = T[\"don_chuan\"]\nd = d[d[\"Trạng thái chuẩn\"] == \"huy\"]"
    plain = "d = T[\"don_tinh_doanh_thu\"]\nanswer = {\"type\": \"number\", \"answer\": len(d)}"
    assert check(_state(full)) is None  # type: ignore[arg-type]
    assert check(_state(plain)) is None  # type: ignore[arg-type]
