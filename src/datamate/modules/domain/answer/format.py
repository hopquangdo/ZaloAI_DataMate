"""Ép kết quả code về đúng format đáp án (rulebook §9); sai thì trả lỗi làm feedback."""

from __future__ import annotations

import math
import re
from collections.abc import Callable, Mapping
from datetime import date, datetime
from typing import Any

import numpy as np
import pandas as pd

from datamate.modules.domain.answer.schema import (
    NO_VALUE_TYPES,
    Answer,
    AnswerType,
    AnswerValue,
    Cell,
    Table,
)

_DATE = re.compile(r"^\d{4}-\d{2}(-\d{2})?$")
_INTEGER_TOLERANCE = 1e-6


class FormatError(ValueError):
    """Đáp án sai format; thông điệp được gửi lại cho LLM."""


def _scalar(value: Any) -> Any:
    if isinstance(value, np.generic):
        return value.item()
    if isinstance(value, (pd.Timestamp, datetime)):
        return value.date().isoformat()
    if isinstance(value, date):
        return value.isoformat()
    return value


def _number(value: Any, where: str) -> int | float:
    value = _scalar(value)
    if isinstance(value, bool) or not isinstance(value, (int, float)) or not math.isfinite(value):
        raise FormatError(f"{where}: cần JSON number hữu hạn, nhận {value!r}")
    if abs(value - round(value)) < _INTEGER_TOLERANCE:
        return round(value)
    return round(float(value), 2)


def _cell(value: Any, where: str) -> Cell:
    value = _scalar(value)
    if isinstance(value, str):
        if not value.strip():
            raise FormatError(f"{where}: chuỗi rỗng")
        return value
    return _number(value, where)


def _list(value: Any) -> tuple[Cell, ...]:
    if isinstance(value, (pd.Series, np.ndarray, tuple)):
        value = list(value)
    if not isinstance(value, list):
        raise FormatError(f"list: cần mảng JSON, nhận {type(value).__name__}")
    return tuple(_cell(v, f"list[{i}]") for i, v in enumerate(value))


def _table(value: Any) -> Table:
    if isinstance(value, pd.DataFrame):
        value = {"columns": list(value.columns), "rows": value.to_numpy().tolist()}
    if not isinstance(value, Mapping) or set(value) != {"columns", "rows"}:
        raise FormatError('table: cần {"columns": [...], "rows": [[...], ...]}')
    columns = tuple(str(c) for c in value["columns"])
    rows: list[tuple[Cell, ...]] = []
    for i, row in enumerate(value["rows"]):
        if len(row) != len(columns):
            raise FormatError(f"table: dòng {i} có {len(row)} ô, cần {len(columns)}")
        rows.append(tuple(_cell(v, f"table.rows[{i}]") for v in row))
    return Table(columns, tuple(rows))


def _date(value: Any) -> str:
    value = _scalar(value)
    if not isinstance(value, str) or not _DATE.match(value):
        raise FormatError(f'date: cần "YYYY-MM-DD" hoặc "YYYY-MM", nhận {value!r}')
    return value


def _string(value: Any) -> str:
    value = _scalar(value)
    if not isinstance(value, str) or not value.strip():
        raise FormatError(f"string: cần chuỗi tên lấy nguyên từ dữ liệu, nhận {value!r}")
    return value.strip()


def _boolean(value: Any) -> bool:
    value = _scalar(value)
    if not isinstance(value, bool):
        raise FormatError(f"boolean: cần true/false, nhận {value!r}")
    return value


def _percent(value: Any) -> float:
    return round(float(_number(value, "percent")), 2)


_COERCERS: dict[AnswerType, Callable[[Any], AnswerValue]] = {
    AnswerType.NUMBER: lambda v: _number(v, "number"),
    AnswerType.PERCENT: _percent,
    AnswerType.STRING: _string,
    AnswerType.DATE: _date,
    AnswerType.BOOLEAN: _boolean,
    AnswerType.LIST: _list,
    AnswerType.TABLE: _table,
}


def coerce_answer(raw: Any) -> Answer:
    """Biến dict của code LLM ({"type", "answer"}) thành ``Answer``, hoặc ném FormatError."""
    if not isinstance(raw, Mapping) or "type" not in raw:
        raise FormatError('biến `answer` phải là dict {"type": ..., "answer": ...}')
    try:
        answer_type = AnswerType(raw["type"])
    except ValueError as error:
        allowed = ", ".join(t.value for t in AnswerType)
        raise FormatError(
            f"type {raw['type']!r} không hợp lệ; chọn một trong: {allowed}"
        ) from error
    if answer_type in NO_VALUE_TYPES:
        reason = raw.get("reason")
        return Answer(answer_type, reason=reason if isinstance(reason, str) else None)
    if "answer" not in raw:
        raise FormatError("thiếu khoá 'answer'")
    return Answer(answer_type, _COERCERS[answer_type](raw["answer"]))
