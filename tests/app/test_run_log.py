import json
from datetime import date

from datamate.app.question import Question
from datamate.app.run_log import Outcome, RunLog
from datamate.modules.domain.answer import ABSTAIN, Answer, AnswerType

QUESTION = Question("q1", "biz_1", "bao nhiêu?", date(2026, 3, 4))
SEVEN = Answer(AnswerType.NUMBER, 7)


def _outcome(error: str | None = None) -> Outcome:
    states = (
        {"attempts": 2, "tokens": 30, "trace": [{"attempt": 1, "error": "lỗi"}, {"attempt": 2}]},
        {"attempts": 1, "tokens": 12, "trace": [{"attempt": 1}]},
    )
    return Outcome(SEVEN, (SEVEN, SEVEN), states, error)  # type: ignore[arg-type]


def test_log_record_keeps_the_documented_keys_in_order() -> None:
    record = RunLog.from_outcome(QUESTION, SEVEN, _outcome(), 1.2345).to_record()
    assert list(record) == [
        "id",
        "business_id",
        "question",
        "as_of_date",
        "answer",
        "samples",
        "attempts",
        "tokens",
        "seconds",
        "error",
        "error_kind",
        "trace",
    ]
    assert record["as_of_date"] == "2026-03-04"
    assert record["answer"] == {"type": "number", "answer": 7}
    assert (record["attempts"], record["tokens"], record["seconds"]) == (3, 42, 1.23)
    assert [step["sample"] for step in record["trace"]] == [0, 0, 1]


def test_api_error_is_labelled_and_everything_stays_plain_json() -> None:
    record = RunLog.from_outcome(
        QUESTION, ABSTAIN, _outcome("APIConnectionError: x"), 0
    ).to_record()
    assert record["error_kind"] == "api"
    json.dumps(record)


def test_failure_log_carries_the_traceback() -> None:
    record = RunLog.failure(QUESTION, ValueError("hỏng"), "Traceback…").to_record()
    assert record["error"] == "ValueError: hỏng"
    assert record["error_kind"] == "bug"
    assert record["traceback"] == "Traceback…"
    assert record["answer"] == {"type": "abstain"}
    assert list(record)[-2:] == ["traceback", "trace"]


def test_long_traceback_is_truncated() -> None:
    record = RunLog.failure(QUESTION, ValueError("x"), "t" * 10_000).to_record()
    assert len(record["traceback"]) <= 4000
