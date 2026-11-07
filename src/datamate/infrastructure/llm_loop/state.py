"""Trạng thái chung của vòng lặp LLM (LangGraph yêu cầu TypedDict)."""

from __future__ import annotations

import operator
from typing import Annotated, Any, TypedDict

from datamate.infrastructure.llm import Message


class TraceStep(TypedDict, total=False):
    """Một dòng nhật ký (chỉ chứa kiểu JSON thuần, ghi thẳng vào run_log)."""

    attempt: int
    code: str
    error: str | None
    answer: dict[str, object]  # Engine.describe(kết quả) của lượt này
    review: str  # tên Check đã bác
    issues: list[str]
    ok: bool
    reason: str
    stopped: str  # lý do dừng sớm


class LoopState(TypedDict, total=False):
    question: str
    messages: list[Message]
    attempts: int
    reply: str  # nguyên văn câu trả lời gần nhất của LLM
    code: str | None
    feedback: str | None
    previous_error: str | None  # lỗi của lượt hỏng gần nhất (để phát hiện lặp lỗi)
    repeats: int  # số lượt liên tiếp hỏng với cùng một lỗi
    candidate: Any  # kết quả hợp lệ gần nhất, chờ soát
    answer: Any  # kết quả cuối cùng (do finalize đặt)
    rejected_by: str | None  # kind của Check để lại feedback hiện tại ("rule" / "llm")
    warned: Annotated[list[str], operator.add]  # luật đã bắn, mỗi luật một lần
    trace: Annotated[list[TraceStep], operator.add]
    tokens: Annotated[int, operator.add]
