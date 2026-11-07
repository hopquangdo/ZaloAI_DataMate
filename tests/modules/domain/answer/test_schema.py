"""Answer là kiểu duy nhất đi qua các module; JSON phải khớp từng byte với định dạng nộp bài."""

import json
from dataclasses import FrozenInstanceError

import pytest

from datamate.modules.domain.answer import ABSTAIN, NO_VALUE_TYPES, Answer, AnswerType, Table


def test_submission_records_keep_the_documented_shape_and_key_order() -> None:
    number = Answer(AnswerType.NUMBER, 5).to_record("q1")
    assert number == {"id": "q1", "type": "number", "answer": 5}
    assert list(number) == ["id", "type", "answer"]
    assert ABSTAIN.to_record("q2") == {"id": "q2", "type": "abstain"}
    unanswerable = Answer.unanswerable("thiếu cột").to_record("q3")
    assert unanswerable == {"id": "q3", "type": "unanswerable", "reason": "thiếu cột"}
    assert Answer(AnswerType.UNANSWERABLE).to_json() == {"type": "unanswerable"}


def test_list_and_table_serialize_as_plain_json() -> None:
    items = Answer(AnswerType.LIST, ("a", 2, 3.5))
    table = Answer(AnswerType.TABLE, Table(("ten", "so"), (("An", 1), ("Bình", 2.5))))
    assert items.to_json() == {"type": "list", "answer": ["a", 2, 3.5]}
    assert table.to_json() == {
        "type": "table",
        "answer": {"columns": ["ten", "so"], "rows": [["An", 1], ["Bình", 2.5]]},
    }
    for answer in (items, table):
        assert json.loads(json.dumps(answer.to_json())) == answer.to_json()  # JSON thuần


def test_no_value_types_have_no_answer_key() -> None:
    assert set(NO_VALUE_TYPES) == {AnswerType.UNANSWERABLE, AnswerType.ABSTAIN}
    assert not ABSTAIN.has_value
    assert "answer" not in Answer.unanswerable("x").to_json()
    assert Answer(AnswerType.BOOLEAN, False).has_value


def test_answers_are_immutable_and_hashable() -> None:
    with pytest.raises(FrozenInstanceError):
        ABSTAIN.reason = "đổi"  # type: ignore[misc]
    assert len({Answer(AnswerType.NUMBER, 1), Answer(AnswerType.NUMBER, 1)}) == 1
