"""Luồng đồ thị agent (generate → execute → review → finalize) với LLM giả."""

from __future__ import annotations

import json
from typing import Any

from datamate.infrastructure.llm import Completion
from datamate.modules.domain.answer import ABSTAIN, Answer, AnswerType
from datamate.modules.solvers.pandas.graph import build_graph
from datamate.modules.solvers.pandas.review import ReviewContext, Verdict, parse_verdict, review
from datamate.modules.solvers.pandas.settings import AgentSettings
from datamate.modules.solvers.pandas.toolkit import unanswerable

GOOD = "```python\nanswer = {'type': 'number', 'answer': 5}\n```"
ZERO = "```python\nanswer = {'type': 'number', 'answer': 0}\n```"
BROKEN = "```python\nanswer = 1 / 0\n```"
OK_JSON = '{"ok": true}'
BAD_JSON = '{"ok": false, "reason": "quên lọc đơn huỷ"}'

FIVE = Answer(AnswerType.NUMBER, 5)
ZERO_ANSWER = Answer(AnswerType.NUMBER, 0)


class ScriptedLLM:
    """Trả lần lượt các câu trả lời đã định; hết thì lặp lại câu cuối."""

    def __init__(self, *replies: str) -> None:
        self._replies = list(replies)
        self.calls = 0

    def complete(self, messages: list[Any]) -> Completion:
        text = self._replies[min(self.calls, len(self._replies) - 1)]
        self.calls += 1
        return Completion(text=text, prompt_tokens=1, completion_tokens=1)


def run(
    llm: ScriptedLLM, *, llm_review: bool = False, attempts: int = 4, repeats: int = 2
) -> dict[str, Any]:
    graph = build_graph(
        llm,  # type: ignore[arg-type]
        lambda: {"unanswerable": unanswerable},
        AgentSettings(max_attempts=attempts, llm_review=llm_review, max_repeats=repeats),
    )
    system = {"role": "system", "content": "sys"}
    user = {"role": "user", "content": "q"}
    state = {"question": "bao nhiêu đơn", "messages": [system, user], "attempts": 0}
    return graph.invoke({**state, "trace": [], "tokens": 0})


def test_clean_answer_takes_one_call() -> None:
    llm = ScriptedLLM(GOOD)
    state = run(llm)
    assert state["answer"] == FIVE
    assert llm.calls == 1


def test_trace_is_plain_json() -> None:
    json.dumps(run(ScriptedLLM(BROKEN, GOOD))["trace"])  # không có DTO lọt vào nhật ký


def test_runtime_error_is_repaired() -> None:
    llm = ScriptedLLM(BROKEN, GOOD)
    assert run(llm)["answer"] == FIVE
    assert llm.calls == 2


def test_always_failing_ends_in_abstain() -> None:
    llm = ScriptedLLM(BROKEN)
    assert run(llm, attempts=3, repeats=0)["answer"] == ABSTAIN
    assert llm.calls == 3


def test_same_error_twice_in_a_row_stops_early() -> None:
    llm = ScriptedLLM(BROKEN)  # lặp đúng một lỗi: dừng sau 2 lượt thay vì dùng hết 4
    state = run(llm, attempts=4, repeats=2)
    assert state["answer"] == ABSTAIN
    assert llm.calls == 2


def test_different_errors_do_not_trigger_early_stop() -> None:
    other = "```python\nanswer = undefined_name\n```"
    llm = ScriptedLLM(BROKEN, other, BROKEN, GOOD)
    assert run(llm, attempts=4, repeats=2)["answer"] == FIVE
    assert llm.calls == 4


def test_rule_warning_fires_once_then_answer_is_kept() -> None:
    llm = ScriptedLLM(ZERO)  # model giữ nguyên kết quả 0 sau khi bị nhắc
    state = run(llm)
    assert state["answer"] == ZERO_ANSWER
    assert llm.calls == 2


def test_failed_repair_falls_back_to_last_valid_candidate() -> None:
    llm = ScriptedLLM(ZERO, BROKEN)
    assert run(llm, attempts=2)["answer"] == ZERO_ANSWER


def test_llm_review_ok_keeps_answer() -> None:
    llm = ScriptedLLM(GOOD, OK_JSON)
    assert run(llm, llm_review=True)["answer"] == FIVE
    assert llm.calls == 2


def test_llm_review_rejecting_to_the_end_abstains() -> None:
    llm = ScriptedLLM(GOOD, BAD_JSON, GOOD, BAD_JSON)
    assert run(llm, llm_review=True, attempts=2)["answer"] == ABSTAIN


def test_llm_review_rejection_then_fixed() -> None:
    llm = ScriptedLLM(ZERO.replace("0", "7"), BAD_JSON, GOOD, OK_JSON)
    assert run(llm, llm_review=True)["answer"] == FIVE
    assert llm.calls == 4


def test_parse_verdict() -> None:
    assert parse_verdict('{"ok": true}') == Verdict(ok=True)
    assert parse_verdict('{"ok": false, "reason": "sai kỳ"}') == Verdict(False, "sai kỳ")
    assert parse_verdict("không phải json") == Verdict(ok=True)


def test_rules() -> None:
    number = Answer(AnswerType.NUMBER, 3)

    def names(question: str, code: str, answer: Answer) -> set[str]:
        return {issue.rule for issue in review(ReviewContext(question, code, answer))}

    assert names("bao nhiêu", "answer = 0", ZERO_ANSWER) == {"empty_result"}
    assert names("bao nhiêu", "answer = 3", number) == set()
    assert "status_not_normalized" in names("x", "df['Trạng thái'] == 'a'", number)
    assert "status_not_normalized" not in names("x", "order_status(df['Trạng thái'])", number)
    assert "time_not_applied" in names("doanh thu tháng 5", "df.sum()", number)
    assert "time_not_applied" not in names("doanh thu tháng 5", "P.month(2025, 5)", number)
    assert names("x", "answer = None", Answer.unanswerable("x")) == set()
    assert "empty_result" in names("x", "", Answer(AnswerType.LIST, ()))
    assert names("x", "", Answer(AnswerType.BOOLEAN, False)) == set()  # False không phải "bằng 0"
