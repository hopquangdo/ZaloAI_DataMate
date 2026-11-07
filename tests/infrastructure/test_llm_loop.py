"""Vòng lặp LLM chung với engine giả: không phụ thuộc pandas hay kiểu đáp án theo đề."""

from __future__ import annotations

import json
import re
from typing import Any

from datamate.infrastructure.llm import Completion
from datamate.infrastructure.llm_loop import (
    AttemptError,
    CheckResult,
    LoopSettings,
    LoopState,
    build_loop,
    initial_state,
)


class ScriptedLLM:
    def __init__(self, *replies: str) -> None:
        self.replies, self.calls = list(replies), 0

    def complete(self, messages: list[Any]) -> Completion:
        text = self.replies[min(self.calls, len(self.replies) - 1)]
        self.calls += 1
        return Completion(text=text, prompt_tokens=2, completion_tokens=3)


class IntEngine:
    """'Code' là một số nguyên trong khối ```int```; số âm coi như lỗi chạy."""

    language = "int"

    def extract(self, reply: str) -> str | None:
        match = re.search(r"```int\n(.*?)\n```", reply, re.S)
        return match.group(1) if match else None

    def run(self, code: str) -> int:
        value = int(code)
        if value < 0:
            raise AttemptError(f"âm: {value}")
        return value

    def describe(self, candidate: int) -> dict[str, Any]:
        return {"value": candidate}


def block(value: int) -> str:
    return f"```int\n{value}\n```"


class RejectZero:
    """Luật rẻ: nhắc một lần khi kết quả là 0."""

    name, kind = "zero", "rule"

    def __call__(self, state: LoopState) -> CheckResult | None:
        if state["candidate"] == 0 and "zero" not in state.get("warned", []):
            return CheckResult(feedback="ra 0, xem lại", names=["zero"])
        return None


class Judge:
    """Check loại llm: bác mọi số khác 7; luôn tốn 10 token."""

    name, kind = "judge", "llm"

    def __call__(self, state: LoopState) -> CheckResult | None:
        ok = state["candidate"] == 7
        return CheckResult(feedback=None if ok else "sai", tokens=10, trace={"ok": ok})


def run(llm: ScriptedLLM, checks=(), **settings: int) -> LoopState:
    loop = build_loop(
        llm, IntEngine(), checks=checks, settings=LoopSettings(**settings), fallback="ABSTAIN"
    )
    return loop.invoke(initial_state("q", [{"role": "user", "content": "q"}]))


def test_valid_result_in_one_call():
    llm = ScriptedLLM(block(5))
    state = run(llm)
    assert state["answer"] == 5 and llm.calls == 1 and state["tokens"] == 5


def test_missing_block_and_runtime_error_are_repaired():
    llm = ScriptedLLM("không có code", block(-1), block(4))
    assert run(llm)["answer"] == 4 and llm.calls == 3


def test_rule_check_nudges_once_then_keeps_result():
    llm = ScriptedLLM(block(0))
    state = run(llm, checks=[RejectZero()])
    assert state["answer"] == 0 and llm.calls == 2


def test_llm_check_rejecting_to_the_end_gives_fallback():
    state = run(ScriptedLLM(block(3)), checks=[Judge()], max_attempts=2, max_repeats=0)
    assert state["answer"] == "ABSTAIN"


def test_passing_llm_check_still_counts_tokens():
    state = run(ScriptedLLM(block(7)), checks=[Judge()])
    assert state["answer"] == 7
    assert state["tokens"] == 5 + 10  # 1 lượt sinh + 1 lượt soát đạt


def test_repeated_identical_error_stops_early():
    llm = ScriptedLLM(block(-1))
    state = run(llm, max_attempts=5, max_repeats=2)
    assert state["answer"] == "ABSTAIN" and llm.calls == 2


def test_trace_is_plain_json():
    state = run(ScriptedLLM(block(-1), block(0), block(7)), checks=[RejectZero(), Judge()])
    json.dumps(state["trace"])
    assert state["answer"] == 7
