from datetime import date

import pytest

from datamate.app.question import Question


def test_parses_a_jsonl_record_once_at_the_boundary() -> None:
    question = Question.from_record(
        {"id": "q_1", "business_id": "biz_9", "question": "hôm nay?", "as_of_date": "2026-03-04"}
    )
    assert question == Question("q_1", "biz_9", "hôm nay?", date(2026, 3, 4))


def test_missing_field_is_reported_by_name() -> None:
    with pytest.raises(ValueError, match="question"):
        Question.from_record({"id": "q", "business_id": "b", "as_of_date": "2026-03-04"})


def test_bad_date_is_rejected_instead_of_guessed() -> None:
    record = {"id": "q", "business_id": "b", "question": "?", "as_of_date": "04/03/2026"}
    with pytest.raises(ValueError, match="as_of_date"):
        Question.from_record(record)
