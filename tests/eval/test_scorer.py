from typing import Any

import pytest

from datamate.core.text import normalize_text
from eval import Verdict, score_answer, score_submission


def ref(type_: str, answer: Any, alias: Any = None) -> dict[str, Any]:
    return {"id": "q", "type": type_, "answer": answer, "alias": alias or []}


def pred(type_: str, answer: Any = None) -> dict[str, Any]:
    return {"id": "q", "type": type_, "answer": answer}


def test_normalize_keeps_diacritics_and_drops_punctuation() -> None:
    assert normalize_text("  Sting DÂU, 330ml!! ") == "sting dâu 330ml"
    assert normalize_text("Cà phê sữa (M)") == "cà phê sữa m"
    assert normalize_text("Sting dâu") != normalize_text("Sting dau")


@pytest.mark.parametrize(
    ("prediction", "expected"),
    [
        (pred("number", 48250000), Verdict.CORRECT),
        (pred("number", 48250000.0), Verdict.CORRECT),
        (pred("number", 48250001), Verdict.WRONG),
        (pred("number", "48250000"), Verdict.WRONG),
        (pred("percent", 48250000), Verdict.WRONG),
        (pred("abstain"), Verdict.ABSTAIN),
        (None, Verdict.ABSTAIN),
    ],
)
def test_number(prediction: dict[str, Any] | None, expected: Verdict) -> None:
    assert score_answer(prediction, ref("number", 48250000)) is expected


def test_percent_rounds_to_two_decimals_and_checks_sign() -> None:
    reference = ref("percent", -12.45)
    assert score_answer(pred("percent", -12.4512), reference) is Verdict.CORRECT
    assert score_answer(pred("percent", 12.45), reference) is Verdict.WRONG


def test_string_accepts_aliases_and_code() -> None:
    reference = ref("string", "Sting dâu 330ml", ["SP0042"])
    assert score_answer(pred("string", "sting  DÂU 330ML"), reference) is Verdict.CORRECT
    assert score_answer(pred("string", "sp0042"), reference) is Verdict.CORRECT
    assert score_answer(pred("string", "Sting dầu 330ml"), reference) is Verdict.WRONG
    assert score_answer(pred("string", ["Sting dâu 330ml"]), reference) is Verdict.WRONG


def test_boolean_is_strict() -> None:
    assert score_answer(pred("boolean", True), ref("boolean", True)) is Verdict.CORRECT
    assert score_answer(pred("boolean", 1), ref("boolean", True)) is Verdict.WRONG


def test_list_is_ordered_with_per_element_alias() -> None:
    reference = ref("list", ["Cà phê sữa (M)", "Bạc xỉu"], [["SP0003"], ["SP0007"]])
    assert score_answer(pred("list", ["SP0003", "bạc xỉu"]), reference) is Verdict.CORRECT
    assert score_answer(pred("list", ["Bạc xỉu", "Cà phê sữa (M)"]), reference) is Verdict.WRONG
    assert score_answer(pred("list", ["Cà phê sữa (M)"]), reference) is Verdict.WRONG


def test_table_rows_are_a_set_and_columns_match_by_name() -> None:
    reference = ref(
        "table",
        {"columns": ["khach_hang", "so_tien_no"], "rows": [["An", 100], ["Bình", 50]]},
        [["KH01"], ["KH02"]],
    )
    swapped = {"columns": ["so tien no", "Khach hang"], "rows": [[50, "KH02"], [100, "an"]]}
    assert score_answer(pred("table", swapped), reference) is Verdict.CORRECT

    positional = {"columns": ["ten", "no"], "rows": [["Bình", 50], ["An", 100]]}
    assert score_answer(pred("table", positional), reference) is Verdict.CORRECT

    wrong_value = {"columns": ["khach_hang", "so_tien_no"], "rows": [["An", 100], ["Bình", 51]]}
    assert score_answer(pred("table", wrong_value), reference) is Verdict.WRONG


def test_unanswerable_only_matches_unanswerable() -> None:
    assert score_answer(pred("unanswerable"), ref("unanswerable", None)) is Verdict.CORRECT
    assert score_answer(pred("number", 0), ref("unanswerable", None)) is Verdict.WRONG
    assert score_answer(pred("unanswerable"), ref("number", 0)) is Verdict.WRONG


def test_penalized_accuracy() -> None:
    references = [
        {"id": "a", "type": "number", "answer": 1, "alias": []},
        {"id": "b", "type": "number", "answer": 2, "alias": []},
        {"id": "c", "type": "number", "answer": 3, "alias": []},
        {"id": "d", "type": "number", "answer": 4, "alias": []},
    ]
    predictions = [
        {"id": "a", "type": "number", "answer": 1},
        {"id": "b", "type": "number", "answer": 2},
        {"id": "c", "type": "number", "answer": 0},
    ]
    assert score_submission(predictions, references).penalized_accuracy == pytest.approx(0.25)
