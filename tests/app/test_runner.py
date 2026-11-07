import json
from datetime import date

import pytest

from datamate.app.pipeline import Result
from datamate.app.question import Question
from datamate.app.run_log import RunLog
from datamate.app.runner import answer_safely, select_questions
from datamate.modules.domain.answer import Answer, AnswerType

QUESTIONS = [Question(f"q{i}", "a" if i % 2 else "b", "?", date(2026, 1, 1)) for i in range(6)]


def test_select_filters_by_business_and_ids() -> None:
    assert {q.business_id for q in select_questions(QUESTIONS, businesses={"a"})} == {"a"}
    assert [q.id for q in select_questions(QUESTIONS, ids={"q2", "q4"})] == ["q2", "q4"]


def test_select_limit_is_a_reproducible_sample() -> None:
    first = select_questions(QUESTIONS, limit=3, seed=7)
    assert len(first) == 3
    assert first == select_questions(QUESTIONS, limit=3, seed=7)


def test_done_questions_are_skipped_after_sampling() -> None:
    remaining = select_questions(QUESTIONS, done={"q1"})
    assert "q1" not in {q.id for q in remaining}
    assert len(remaining) == len(QUESTIONS) - 1


class _Pipeline:
    def __init__(self, error: Exception | None = None) -> None:
        self._error = error

    def answer(self, question: Question) -> Result:
        if self._error:
            raise self._error
        answer = Answer(AnswerType.NUMBER, 1)
        return Result(answer, RunLog(question, answer))


def test_success_passes_through() -> None:
    result = answer_safely(_Pipeline(), QUESTIONS[0])  # type: ignore[arg-type]
    assert result.record == {"id": "q0", "type": "number", "answer": 1}


def test_bug_becomes_a_loud_abstain_with_traceback() -> None:
    result = answer_safely(_Pipeline(ValueError("hỏng")), QUESTIONS[0])  # type: ignore[arg-type]
    assert result.record == {"id": "q0", "type": "abstain"}
    assert result.log.error_kind == "bug"
    assert result.log.error == "ValueError: hỏng"
    assert "ValueError" in (result.log.traceback or "")
    json.dumps(result.log.to_record())


def test_strict_mode_raises_the_bug() -> None:
    with pytest.raises(ValueError, match="hỏng"):
        answer_safely(_Pipeline(ValueError("hỏng")), QUESTIONS[0], strict=True)  # type: ignore[arg-type]
