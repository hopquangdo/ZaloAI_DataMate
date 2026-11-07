"""Luật review rẻ (không gọi LLM): bắt các dấu hiệu đáp án sai logic dù code chạy trơn tru.

Mỗi luật nhận ngữ cảnh và trả về lời nhắc (str) hoặc None. Giữ luật bảo thủ: mỗi lần bắn
tốn một lượt sửa, và luật đã bắn một lần sẽ không bắn lại cho cùng câu hỏi.
"""

from __future__ import annotations

import re
from collections.abc import Callable, Collection
from dataclasses import dataclass

from datamate.core.text import fold
from datamate.modules.domain.answer import Answer, Table

_STATUS_WORDS = ("trang thai", "tinh trang", "status")
_TIME_WORDS = re.compile(r"\b(thang|quy|tuan|hom nay|hom qua|tet|nam nay|nam ngoai)\b")
_TIME_TOOLS = ("P.", ".dt", "today", "lunar", "date(")


@dataclass(frozen=True, slots=True)
class ReviewContext:
    """Những gì một luật cần để quyết định: câu hỏi, code và đáp án."""

    question: str
    code: str
    answer: Answer


@dataclass(frozen=True, slots=True)
class Issue:
    """Một vấn đề do luật `rule` phát hiện, kèm lời nhắc gửi lại cho model."""

    rule: str
    message: str


Rule = Callable[[ReviewContext], str | None]


def _empty_result(ctx: ReviewContext) -> str | None:
    value = ctx.answer.value
    is_zero = isinstance(value, (int, float)) and not isinstance(value, bool) and value == 0
    is_empty = value == () or (isinstance(value, Table) and not value.rows)
    if is_zero or is_empty:
        return (
            "Kết quả rỗng hoặc bằng 0. Kiểm tra lại bộ lọc (kỳ thời gian, trạng thái đơn, "
            "tên lấy từ dữ liệu). Nếu dữ liệu thật sự cho kết quả này thì giữ nguyên code."
        )
    return None


def _status_not_normalized(ctx: ReviewContext) -> str | None:
    uses_status = any(word in fold(ctx.code) for word in _STATUS_WORDS)
    if uses_status and "order_status(" not in ctx.code:
        return (
            "Code dùng cột trạng thái nhưng không qua order_status(). "
            "Hãy lọc đơn bằng order_status theo rulebook."
        )
    return None


def _time_not_applied(ctx: ReviewContext) -> str | None:
    asks_time = _TIME_WORDS.search(fold(ctx.question)) is not None
    if asks_time and not any(tool in ctx.code for tool in _TIME_TOOLS):
        return (
            "Câu hỏi có kỳ thời gian nhưng code không lọc theo thời gian. "
            "Hãy dùng P.* / today / lunar theo rulebook §2."
        )
    return None


RULES: dict[str, Rule] = {
    "empty_result": _empty_result,
    "status_not_normalized": _status_not_normalized,
    "time_not_applied": _time_not_applied,
}


def review(ctx: ReviewContext, skip: Collection[str] = ()) -> list[Issue]:
    """Các vấn đề do luật phát hiện, bỏ qua luật đã bắn trước đó."""
    if not ctx.answer.has_value:
        return []
    found = ((name, rule(ctx)) for name, rule in RULES.items() if name not in skip)
    return [Issue(name, message) for name, message in found if message]
