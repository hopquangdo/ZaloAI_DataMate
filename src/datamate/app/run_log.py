"""Bản ghi log cho từng câu hỏi (ghi vào run_log.jsonl)."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Literal, cast

from datamate.app.question import Question
from datamate.core.text import shorten
from datamate.infrastructure.llm_loop import LoopState, TraceStep
from datamate.modules.domain.answer import ABSTAIN, Answer

ErrorKind = Literal["api", "bug"]  # api: lỗi gọi LLM; bug: lỗi chương trình

MAX_TRACEBACK_CHARS = 4000


class LoggedStep(TraceStep, total=False):
    """Dòng nhật ký của đồ thị, kèm số thứ tự lần sinh."""

    sample: int  # lần sinh thứ mấy trong bỏ phiếu


@dataclass(frozen=True, slots=True)
class Outcome:
    """Kết quả các lần sinh của một câu hỏi, trước khi chốt đáp án."""

    winner: Answer | None
    samples: tuple[Answer, ...]
    states: tuple[LoopState, ...]
    error: str | None
    sources: tuple[str, ...] = ()  # bộ giải sinh ra từng mẫu (cùng thứ tự với samples)


@dataclass(frozen=True, slots=True)
class RunLog:
    """Log của một câu hỏi, ghi vào run_log.jsonl qua to_record()."""

    question: Question
    answer: Answer
    samples: tuple[Answer, ...] = ()
    sources: tuple[str, ...] = ()
    attempts: int = 0
    tokens: int = 0
    seconds: float = 0.0
    error: str | None = None
    error_kind: ErrorKind | None = None
    traceback: str | None = None
    trace: tuple[LoggedStep, ...] = ()

    @classmethod
    def from_outcome(
        cls, question: Question, answer: Answer, outcome: Outcome, seconds: float
    ) -> RunLog:
        """Log của câu đã chạy xong (có thể kèm lỗi gọi API ở một số lần sinh)."""
        return cls(
            question=question,
            answer=answer,
            samples=outcome.samples,
            sources=outcome.sources,
            attempts=sum(state.get("attempts", 0) for state in outcome.states),
            tokens=sum(state.get("tokens", 0) for state in outcome.states),
            seconds=round(seconds, 2),
            error=outcome.error,
            error_kind="api" if outcome.error else None,
            trace=tuple(
                cast(LoggedStep, {"sample": index, **step})
                for index, state in enumerate(outcome.states)
                for step in state.get("trace", [])
            ),
        )

    @classmethod
    def failure(cls, question: Question, error: BaseException, traceback_text: str) -> RunLog:
        """Log của câu bị lỗi chương trình: giữ traceback để sửa lỗi."""
        return cls(
            question=question,
            answer=ABSTAIN,
            error=f"{type(error).__name__}: {error}",
            error_kind="bug",
            traceback=shorten(traceback_text, MAX_TRACEBACK_CHARS),
        )

    def to_record(self) -> dict[str, Any]:
        """Dòng của run_log.jsonl; chỉ chứa kiểu JSON thuần."""
        record: dict[str, Any] = {
            "id": self.question.id,
            "business_id": self.question.business_id,
            "question": self.question.text,
            "as_of_date": self.question.as_of_date.isoformat(),
            "answer": self.answer.to_json(),
            "samples": [sample.to_json() for sample in self.samples],
            "sources": list(self.sources),
            "attempts": self.attempts,
            "tokens": self.tokens,
            "seconds": self.seconds,
            "error": self.error,
            "error_kind": self.error_kind,
        }
        if self.traceback is not None:
            record["traceback"] = self.traceback
        record["trace"] = [dict(step) for step in self.trace]
        return record
