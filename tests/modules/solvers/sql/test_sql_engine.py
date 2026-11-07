"""Bộ giải SQL: hợp đồng đầu ra, chặn lệnh nguy hiểm, hàm nghiệp vụ, và vòng lặp với LLM giả."""

from __future__ import annotations

from typing import Any

import pandas as pd
import pytest

from datamate.infrastructure.llm import Completion
from datamate.infrastructure.llm_loop import AttemptError, initial_state
from datamate.modules.domain.answer import ABSTAIN, Answer, AnswerType
from datamate.modules.solvers.sql import SqlEngine, build_sql_graph

ORDERS = pd.DataFrame(
    {
        "Mã đơn": ["D1", "D2", "D3", "D4"],
        "Ngày": pd.to_datetime(["2026-03-01", "2026-03-02", "2026-03-02", "2026-04-01"]),
        "Tên hàng": ["Cà phê sữa", "Trà đào", "Cà phê sữa", "Trà đào"],
        "Tiền": [10000.0, 20000.0, 30000.0, 40000.0],
        "Trạng thái": ["xong", "Đã hủy", "Hoàn thành", "xong"],
    }
)


def engine() -> SqlEngine:
    return SqlEngine(lambda: {"Đơn hàng": ORDERS})


def block(body: str) -> str:
    return f"```sql\n{body}\n```"


def run(body: str) -> Answer:
    e = engine()
    return e.run(e.extract(block(body)))


def test_scalar_with_business_functions() -> None:
    answer = run(
        '-- type: number\nSELECT round_money(SUM("Tiền")) FROM "Đơn hàng"\n'
        "WHERE order_status(\"Trạng thái\") IN ('hoan_thanh', 'dang_giao')\n"
        "AND CAST(\"Ngày\" AS DATE) BETWEEN DATE '2026-03-01' AND DATE '2026-03-31'"
    )
    assert answer == Answer(AnswerType.NUMBER, 40000)


def test_fold_matches_unaccented_names() -> None:
    answer = run(
        '-- type: number\nSELECT COUNT(*) FROM "Đơn hàng" WHERE fold("Tên hàng") = \'ca phe sua\''
    )
    assert answer.value == 2


def test_list_and_table_shapes() -> None:
    names = run('-- type: list\nSELECT DISTINCT "Tên hàng" FROM "Đơn hàng" ORDER BY 1')
    assert names.value == ("Cà phê sữa", "Trà đào")
    table = run('-- type: table\nSELECT "Tên hàng", SUM("Tiền") AS tien FROM "Đơn hàng" GROUP BY 1')
    assert table.type is AnswerType.TABLE


def test_unanswerable_marker() -> None:
    e = engine()
    assert e.run("-- unanswerable: không ghi kho").type is AnswerType.UNANSWERABLE


@pytest.mark.parametrize(
    ("body", "message"),
    [
        ("SELECT 1", "type"),
        ('-- type: number\nDROP TABLE "Đơn hàng"', "SELECT"),
        ("-- type: number\nSELECT 1; SELECT 2", "MỘT câu"),
        ("-- type: number\nSELECT * FROM read_csv('x.csv')", "read_csv"),
        ('-- type: number\nSELECT "Tiền" FROM "Đơn hàng"', "1 dòng"),
        ('-- type: number\nSELECT "Không có" FROM "Đơn hàng"', "Error"),
        ("-- type: nonsense\nSELECT 1", "không hợp lệ"),
    ],
)
def test_rejections_become_feedback(body: str, message: str) -> None:
    with pytest.raises(AttemptError, match=message):
        run(body)


class ScriptedLLM:
    def __init__(self, *replies: str) -> None:
        self.replies, self.calls = list(replies), 0

    def complete(self, messages: list[Any]) -> Completion:
        text = self.replies[min(self.calls, len(self.replies) - 1)]
        self.calls += 1
        return Completion(text=text, prompt_tokens=1, completion_tokens=1)


def test_loop_repairs_a_broken_query() -> None:
    llm = ScriptedLLM(
        block('-- type: number\nSELECT "Sai" FROM "Đơn hàng"'),
        block('-- type: number\nSELECT COUNT(*) FROM "Đơn hàng"'),
    )
    graph = build_sql_graph(llm, lambda: {"Đơn hàng": ORDERS})  # type: ignore[arg-type]
    state = graph.invoke(initial_state("?", [{"role": "user", "content": "?"}]))
    assert state["answer"] == Answer(AnswerType.NUMBER, 4) and llm.calls == 2


def test_loop_gives_abstain_when_never_valid() -> None:
    llm = ScriptedLLM("không có sql")
    graph = build_sql_graph(llm, lambda: {"Đơn hàng": ORDERS})  # type: ignore[arg-type]
    assert graph.invoke(initial_state("?", []))["answer"] == ABSTAIN


def test_pandas_style_table_refs_are_rewritten() -> None:
    answer = run('-- type: number\nSELECT COUNT(*) FROM T["Đơn hàng"] WHERE T["Đơn hàng"]["Tiền"] > 15000')
    assert answer.value == 3
