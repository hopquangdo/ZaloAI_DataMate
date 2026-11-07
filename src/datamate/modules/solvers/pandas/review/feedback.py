"""Soạn feedback gửi lại cho bước generate, kèm đáp án cũ để model biết đang bị nhắc về gì."""

from __future__ import annotations

import json

from datamate.core.text import shorten
from datamate.modules.domain.answer import Answer

MAX_ANSWER_CHARS = 600


def answer_text(answer: Answer) -> str:
    """Đáp án dạng JSON, cắt ngắn để không làm phình prompt."""
    return shorten(json.dumps(answer.to_json(), ensure_ascii=False), MAX_ANSWER_CHARS)


def review_feedback(answer: Answer, issues: list[str]) -> str:
    """Feedback gửi lại cho generate: đáp án cũ và các vấn đề cần sửa."""
    lines = [f"Code chạy được và cho kết quả: {answer_text(answer)}", "Nhưng có vấn đề:"]
    lines += [f"- {issue}" for issue in issues]
    return "\n".join(lines)
