"""Lỗi và tín hiệu của sandbox."""

from __future__ import annotations


class CodeRejected(ValueError):  # noqa: N818 — tên nằm trong feedback gửi LLM
    """Code vi phạm luật sandbox."""


class ExecutionFailed(RuntimeError):  # noqa: N818 — tên nằm trong feedback gửi LLM
    """Code chạy lỗi; thông điệp là traceback rút gọn để gửi lại LLM."""


class Unanswerable(Exception):  # noqa: N818 — tín hiệu điều khiển, không phải lỗi
    """Code gọi unanswerable(reason): dữ liệu không đủ để trả lời."""

    def __init__(self, reason: str) -> None:
        super().__init__(reason)
        self.reason = reason
