"""Đáp án theo đề (docs/TASK.md §6.1): kiểu đáp án và ép về đúng format. Mọi tầng dùng chung."""

from datamate.modules.domain.answer.format import FormatError, coerce_answer
from datamate.modules.domain.answer.schema import (
    ABSTAIN,
    NO_VALUE_TYPES,
    Answer,
    AnswerType,
    AnswerValue,
    Cell,
    Table,
)

__all__ = [
    "ABSTAIN",
    "NO_VALUE_TYPES",
    "Answer",
    "AnswerType",
    "AnswerValue",
    "Cell",
    "FormatError",
    "Table",
    "coerce_answer",
]
