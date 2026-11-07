"""Một câu hỏi đầu vào, đã parse ngay ở biên (đọc questions.jsonl)."""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
from datetime import date
from typing import Any


@dataclass(frozen=True, slots=True)
class Question:
    """Một câu hỏi: id, doanh nghiệp, nội dung và ngày "hôm nay"."""

    id: str
    business_id: str
    text: str
    as_of_date: date  # "hôm nay" của câu hỏi

    @classmethod
    def from_record(cls, record: Mapping[str, Any]) -> Question:
        """Từ một dòng của questions.jsonl; thiếu khoá hoặc sai ngày thì báo rõ, không đoán."""
        try:
            return cls(
                id=record["id"],
                business_id=record["business_id"],
                text=record["question"],
                as_of_date=date.fromisoformat(record["as_of_date"]),
            )
        except KeyError as error:
            raise ValueError(f"câu hỏi thiếu trường {error}: {dict(record)!r}") from error
        except (TypeError, ValueError) as error:
            raise ValueError(f"câu hỏi có as_of_date sai định dạng: {dict(record)!r}") from error
