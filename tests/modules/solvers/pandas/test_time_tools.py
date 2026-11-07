"""Các lỗi Qwen từng mắc với toolkit nay phải chạy được."""

from datetime import date
from pathlib import Path

import pandas as pd
import pytest

from datamate.infrastructure.llm_loop import AttemptError
from datamate.modules.data.ingestion import Business
from datamate.modules.domain.periods import LunarCalendar
from datamate.modules.solvers.pandas.engine import PandasEngine
from datamate.modules.solvers.pandas.time_tools import PeriodTools
from datamate.modules.solvers.pandas.toolkit import build_namespace

TRAIN = Path("dataset/train/train")


def namespace() -> dict:
    orders = pd.DataFrame(
        {
            "Ngày": pd.to_datetime(["2025-10-18", "2025-10-19", "2025-10-20"]),
            "Tiền": [1.0, 2.0, 3.0],
        }
    )
    lunar = LunarCalendar.load(TRAIN / "calendar.csv") if TRAIN.exists() else None
    return build_namespace(Business("b", "", {"don": orders}), date(2025, 10, 20), lunar)


def run(code: str) -> object:
    engine = PandasEngine(namespace)
    return engine.run(code).value


def test_day_accepts_three_ints() -> None:
    p = PeriodTools()
    assert p.day(2025, 10, 19) == p.day(date(2025, 10, 19))


def test_period_bounds_compare_with_datetime_column() -> None:
    code = """
p = P.day(2025, 10, 19)
df = T["don"]
answer = {"type": "number", "answer": df[(df["Ngày"] >= p.start) & (df["Ngày"] <= p.end)]["Tiền"].sum()}
"""
    assert run(code) == 2


def test_today_compares_with_datetime_column_and_timedelta_is_available() -> None:
    code = """
df = T["don"]
answer = {"type": "number", "answer": df[df["Ngày"] > today - timedelta(days=2)]["Tiền"].sum()}
"""
    assert run(code) == 5


def test_period_helpers_accept_timestamp_today() -> None:
    code = 'answer = {"type": "number", "answer": P.last_n_days(today, 3).days}'
    assert run(code) == 3


def test_unknown_period_function_lists_real_names() -> None:
    with pytest.raises(AttemptError, match="Các hàm có sẵn"):
        run('answer = {"type": "number", "answer": P.n_days(today, 3).days}')


def test_missing_column_suggests_close_names() -> None:
    with pytest.raises(AttemptError, match=r'T\["don"\]\["Ngày"\]'):
        run('answer = {"type": "number", "answer": T["don"]["Ngay"].count()}')


def test_yesterday_alias() -> None:
    code = 'answer = {"type": "number", "answer": T["don"][P.yesterday(today).contains(T["don"]["Ngày"])]["Tiền"].sum()}'
    assert run(code) == 2
