"""Engine pandas cho vòng lặp LLM: chạy code trong sandbox, ép kết quả về đáp án theo đề."""

from __future__ import annotations

import difflib
import re
from collections.abc import Callable
from typing import Any

from datamate.infrastructure.llm_loop import AttemptError
from datamate.infrastructure.llm_output import extract_code
from datamate.modules.domain.answer import Answer, FormatError, coerce_answer
from datamate.modules.solvers.pandas.sandbox import (
    CodeRejected,
    ExecutionFailed,
    Unanswerable,
    run_code,
)


class PandasEngine:
    """LLM viết code Python gán biến ``answer``; mỗi lượt chạy trên một namespace mới."""

    language = "python"

    def __init__(self, namespace_factory: Callable[[], dict[str, Any]]) -> None:
        self._namespace_factory = namespace_factory

    def extract(self, reply: str) -> str | None:
        return extract_code(reply)

    def run(self, code: str) -> Answer:
        try:
            return coerce_answer(run_code(code, self._namespace_factory()))
        except Unanswerable as signal:
            return Answer.unanswerable(signal.reason)
        except (CodeRejected, ExecutionFailed, FormatError) as error:
            message = f"{type(error).__name__}: {error}"
            raise AttemptError(message + self._column_hint(message)) from error

    def _column_hint(self, message: str) -> str:
        """KeyError tên cột → gợi ý các cột gần giống và bảng chứa chúng."""
        match = re.search(r"KeyError: ['\"](.+?)['\"]", message)
        if match is None:
            return ""
        missing = match.group(1)
        tables: dict[str, Any] = self._namespace_factory().get("T", {})
        if missing in tables:
            return ""
        pairs = [(name, str(col)) for name, table in tables.items() for col in table.columns]
        close = set(difflib.get_close_matches(missing, [col for _, col in pairs], n=6, cutoff=0.5))
        hits = [f'T["{name}"]["{col}"]' for name, col in pairs if col in close][:8]
        if not hits:
            return f"\nKhông có cột '{missing}'. Xem lại tên bảng và cột trong mô tả bảng."
        return f"\nKhông có cột '{missing}' ở bảng đã dùng. Các cột gần giống: " + ", ".join(hits)

    def describe(self, candidate: Answer) -> dict[str, Any]:
        return candidate.to_json()
