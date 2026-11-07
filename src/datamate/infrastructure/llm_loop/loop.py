"""Vòng lặp LLM dùng chung: generate → execute → check… → finalize.

    generate ─→ execute ─→ check_1 ─→ … ─→ check_n ─→ finalize ─→ END
       ↑__________ còn feedback và còn lượt ____________|

Mọi vấn đề (không có code, bị chặn, lỗi chạy, sai format, bị Check bác) đều thành feedback và dùng
chung một bộ đếm lượt. Dừng sớm khi cùng một lỗi lặp lại liên tiếp ``max_repeats`` lượt.
"""

from __future__ import annotations

from collections.abc import Callable, Sequence
from dataclasses import dataclass
from typing import Any, Literal

from langgraph.graph import END, START, StateGraph

from datamate.core.text import shorten
from datamate.infrastructure.llm import LLMClient
from datamate.infrastructure.llm_loop.engine import AttemptError, Check, Engine
from datamate.infrastructure.llm_loop.state import LoopState
from datamate.infrastructure.prompt_loader import render_prompt

Route = Literal["ok", "retry", "give_up"]
_MAX_PREVIOUS_REPLY_CHARS = 2000


@dataclass(frozen=True)
class LoopSettings:
    max_attempts: int = 4  # 1 lần sinh + tối đa 3 lần sửa
    max_repeats: int = 2  # cùng một lỗi liên tiếp bao nhiêu lượt thì dừng (0 = không dừng sớm)
    repair_prompt: str = "repair"  # tên prompt sửa lỗi trong assets/prompts


def _previous_turn(state: LoopState, language: str) -> str:
    code = state.get("code")
    if code:
        return f"```{language}\n{code}\n```"
    return shorten(state.get("reply") or "", _MAX_PREVIOUS_REPLY_CHARS) or "(không có nội dung)"


def _generate(llm: LLMClient, engine: Engine, settings: LoopSettings) -> Callable[..., LoopState]:
    def generate(state: LoopState) -> LoopState:
        messages = list(state["messages"])
        feedback = state.get("feedback")
        if feedback:
            messages += [
                {"role": "assistant", "content": _previous_turn(state, engine.language)},
                {
                    "role": "user",
                    "content": render_prompt(settings.repair_prompt, feedback=feedback),
                },
            ]
        completion = llm.complete(messages)
        code = engine.extract(completion.text)
        missing = f"Không tìm thấy khối ```{engine.language}``` trong câu trả lời."
        return {
            "attempts": state.get("attempts", 0) + 1,
            "reply": completion.text,
            "code": code,
            "feedback": None if code else missing,
            "tokens": completion.prompt_tokens + completion.completion_tokens,
        }

    return generate


def _failed(state: LoopState, error: str, code: str | None) -> LoopState:
    repeats = state.get("repeats", 0) + 1 if error == state.get("previous_error") else 1
    step: dict[str, Any] = {"attempt": state["attempts"], "error": error}
    if code:
        step["code"] = code
    return {"feedback": error, "previous_error": error, "repeats": repeats, "trace": [step]}


def _execute(engine: Engine) -> Callable[..., LoopState]:
    def execute(state: LoopState) -> LoopState:
        code = state.get("code")
        if not code:
            return _failed(state, state.get("feedback") or "không có code", None)
        try:
            candidate = engine.run(code)
        except AttemptError as error:
            return _failed(state, str(error), code)
        return {
            "candidate": candidate,
            "feedback": None,
            "rejected_by": None,
            "previous_error": None,
            "repeats": 0,
            "trace": [
                {"attempt": state["attempts"], "code": code, "answer": engine.describe(candidate)}
            ],
        }

    return execute


def _check(check: Check) -> Callable[..., LoopState]:
    def node(state: LoopState) -> LoopState:
        if state.get("candidate") is None:
            return {}
        result = check(state)
        if result is None:
            return {}
        step = {"attempt": state["attempts"], "review": check.name, **result.trace}
        update: LoopState = {"tokens": result.tokens, "trace": [step]}
        if result.rejected:
            update |= {
                "feedback": result.feedback,
                "rejected_by": check.kind,
                "warned": result.names,
            }
        return update

    return node


def _finalize(fallback: Any) -> Callable[..., LoopState]:
    """Bị check loại "llm" bác đến cùng → fallback; còn lại giữ kết quả hợp lệ gần nhất."""

    def finalize(state: LoopState) -> LoopState:
        if state.get("feedback") and state.get("rejected_by") == "llm":
            return {"answer": fallback}
        candidate = state.get("candidate")
        return {"answer": fallback if candidate is None else candidate}

    return finalize


def _route(settings: LoopSettings) -> Callable[[LoopState], Route]:
    def route(state: LoopState) -> Route:
        if not state.get("feedback"):
            return "ok"
        if settings.max_repeats and state.get("repeats", 0) >= settings.max_repeats:
            return "give_up"
        return "retry" if state.get("attempts", 0) < settings.max_attempts else "give_up"

    return route


def build_loop(
    llm: LLMClient,
    engine: Engine,
    *,
    checks: Sequence[Check] = (),
    settings: LoopSettings | None = None,
    fallback: Any = None,
) -> Any:
    """Dựng và biên dịch vòng lặp; ``fallback`` là kết quả khi không có gì hợp lệ (vd. ABSTAIN)."""
    settings = settings or LoopSettings()
    route = _route(settings)
    branches = {"retry": "generate", "give_up": "finalize"}
    graph = StateGraph(LoopState)
    graph.add_node("generate", _generate(llm, engine, settings))
    graph.add_node("execute", _execute(engine))
    graph.add_node("finalize", _finalize(fallback))
    graph.add_edge(START, "generate")
    graph.add_edge("generate", "execute")

    names = [f"check_{i}_{check.name}" for i, check in enumerate(checks)]
    for name, check in zip(names, checks, strict=True):
        graph.add_node(name, _check(check))
    after = [*names, "finalize"]
    graph.add_conditional_edges("execute", route, {"ok": after[0], **branches})
    for name, nxt in zip(names, after[1:], strict=True):
        graph.add_conditional_edges(name, route, {"ok": nxt, **branches})
    graph.add_edge("finalize", END)
    return graph.compile()


def initial_state(question: str, messages: list[Any]) -> LoopState:
    """Trạng thái khởi đầu cho ``graph.invoke``."""
    return {
        "question": question,
        "messages": list(messages),
        "attempts": 0,
        "trace": [],
        "tokens": 0,
    }
