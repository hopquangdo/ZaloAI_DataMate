import numpy as np
import pandas as pd
import pytest

from datamate.modules.domain.answer import Answer, AnswerType, FormatError, Table, coerce_answer


def test_coerce_numbers_and_numpy() -> None:
    assert coerce_answer({"type": "number", "answer": np.float64(48250000.0)}) == Answer(
        AnswerType.NUMBER, 48250000
    )
    assert coerce_answer({"type": "percent", "answer": -12.4512}).value == -12.45
    assert coerce_answer({"type": "date", "answer": pd.Timestamp("2025-09-01")}).value == (
        "2025-09-01"
    )


def test_coerce_rejects_wrong_formats() -> None:
    with pytest.raises(FormatError):
        coerce_answer({"type": "number", "answer": "48.250.000"})
    with pytest.raises(FormatError):
        coerce_answer({"type": "boolean", "answer": 1})
    with pytest.raises(FormatError):
        coerce_answer({"type": "money", "answer": 1})
    with pytest.raises(FormatError):
        coerce_answer({"type": "number"})
    with pytest.raises(FormatError):
        coerce_answer([1, 2])


def test_coerce_list_is_an_immutable_tuple() -> None:
    answer = coerce_answer({"type": "list", "answer": pd.Series(["An", 2.0])})
    assert answer.value == ("An", 2)


def test_coerce_table_from_dataframe() -> None:
    frame = pd.DataFrame({"khach_hang": ["An"], "so_tien_no": [np.int64(3200000)]})
    answer = coerce_answer({"type": "table", "answer": frame})
    assert answer.value == Table(("khach_hang", "so_tien_no"), (("An", 3200000),))
    assert answer.to_json()["answer"] == {
        "columns": ["khach_hang", "so_tien_no"],
        "rows": [["An", 3200000]],
    }


def test_coerce_table_checks_shape() -> None:
    with pytest.raises(FormatError):
        coerce_answer({"type": "table", "answer": {"columns": ["a", "b"], "rows": [[1]]}})
    with pytest.raises(FormatError):
        coerce_answer({"type": "table", "answer": {"columns": ["a"]}})


def test_no_value_types_keep_only_a_string_reason() -> None:
    assert coerce_answer({"type": "unanswerable", "reason": "thiếu cột"}) == Answer.unanswerable(
        "thiếu cột"
    )
    assert coerce_answer({"type": "unanswerable", "reason": 5}) == Answer(AnswerType.UNANSWERABLE)
    assert coerce_answer({"type": "abstain"}) == Answer(AnswerType.ABSTAIN)
