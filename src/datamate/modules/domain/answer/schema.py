"""Kiểu đáp án theo đề (TASK.md §6.1) và dạng giá trị của từng kiểu.

``Answer`` là kiểu duy nhất đi qua các module; JSON chỉ xuất hiện ở hai biên: code do LLM sinh
ra (``format.coerce_answer`` biến nó thành ``Answer``) và file nộp bài / log (``to_json``).
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import Any

Cell = int | float | str


class AnswerType(str, Enum):
    """Các kiểu đáp án theo đề."""

    NUMBER = "number"
    PERCENT = "percent"
    STRING = "string"
    DATE = "date"
    BOOLEAN = "boolean"
    LIST = "list"
    TABLE = "table"
    UNANSWERABLE = "unanswerable"
    ABSTAIN = "abstain"


# Kiểu không mang giá trị: không có khoá "answer" để soát hay so khớp.
NO_VALUE_TYPES: frozenset[AnswerType] = frozenset({AnswerType.UNANSWERABLE, AnswerType.ABSTAIN})


@dataclass(frozen=True, slots=True)
class Table:
    """Bảng đáp án: tên cột và các dòng (bất biến, so sánh và băm được)."""

    columns: tuple[str, ...]
    rows: tuple[tuple[Cell, ...], ...]


AnswerValue = int | float | str | bool | tuple[Cell, ...] | Table


@dataclass(frozen=True, slots=True)
class Answer:
    """Một đáp án hợp lệ. ``value`` rỗng với unanswerable/abstain; ``reason`` là lý do (nếu có)."""

    type: AnswerType
    value: AnswerValue | None = None
    reason: str | None = None

    @classmethod
    def unanswerable(cls, reason: str) -> Answer:
        return cls(AnswerType.UNANSWERABLE, reason=reason)

    @property
    def has_value(self) -> bool:
        return self.type not in NO_VALUE_TYPES

    def to_json(self) -> dict[str, Any]:
        """Dạng JSON theo đề: {"type", "answer"?, "reason"?}."""
        data: dict[str, Any] = {"type": self.type.value}
        if self.has_value:
            data["answer"] = _json_value(self.value)
        if self.reason is not None:
            data["reason"] = self.reason
        return data

    def to_record(self, question_id: str) -> dict[str, Any]:
        """Một dòng của submission.jsonl."""
        return {"id": question_id, **self.to_json()}


ABSTAIN = Answer(AnswerType.ABSTAIN)


def _json_value(value: AnswerValue | None) -> Any:
    if isinstance(value, Table):
        return {"columns": list(value.columns), "rows": [list(row) for row in value.rows]}
    if isinstance(value, tuple):
        return list(value)
    return value
