from datamate.modules.solvers.threshold_days import ThresholdDaysCheck

SQL_BAD = (
    "SELECT COUNT(DISTINCT CAST(\"Ngày đặt\" AS DATE)) FROM \"don_tinh_doanh_thu\"\n"
    "WHERE \"Doanh thu đơn\" >= 9600000"
)
SQL_GOOD = (
    "SELECT COUNT(*) FROM (SELECT CAST(\"Ngày đặt\" AS DATE) d FROM \"don_tinh_doanh_thu\" "
    "GROUP BY d HAVING SUM(\"Doanh thu đơn\") >= 9600000)"
)
PANDAS_BAD = 'n = d[d["Doanh thu đơn"] >= 9600000]["Ngày đặt"].dt.date.nunique()'


def _state(code: str, warned: list[str] | None = None) -> dict:
    return {"code": code, "warned": warned or []}


def test_row_level_threshold_with_distinct_days_is_flagged_once() -> None:
    check = ThresholdDaysCheck()
    got = check(_state(SQL_BAD))  # type: ignore[arg-type]
    assert got is not None and got.rejected
    assert check(_state(PANDAS_BAD)) is not None  # type: ignore[arg-type]
    assert check(_state(SQL_BAD, got.names)) is None  # type: ignore[arg-type]


def test_aggregated_by_day_is_fine() -> None:
    assert ThresholdDaysCheck()(_state(SQL_GOOD)) is None  # type: ignore[arg-type]
