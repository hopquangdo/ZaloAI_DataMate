import pytest

from datamate.modules.understanding.normalize import normalize_question
from datamate.modules.understanding.normalize.telex import decode_word


@pytest.mark.parametrize(
    ("typed", "expected"),
    [
        ("dduwowcj", "được"),
        ("toongr", "tổng"),
        ("cuwar", "cửa"),
        ("bans", "bán"),
        ("heets", "hết"),
        ("cuoois", "cuối"),
        ("thangs", "tháng"),
        ("ddown", "đơn"),
        ("laf", "là"),
        ("bij", "bị"),
    ],
)
def test_decodes_leftover_telex(typed: str, expected: str) -> None:
    assert decode_word(typed) == expected


@pytest.mark.parametrize("word", ["gas", "box", "max", "Max", "Panadol", "sales", "size", "top", "k"])
def test_leaves_foreign_words_and_names_alone(word: str) -> None:
    assert decode_word(word) == word


def test_question_normalization_combines_telex_and_abbreviations() -> None:
    assert normalize_question("bữa qua toongr cộng bán dduwowcj bnhiu lon") == (
        "bữa qua tổng cộng bán được bao nhiêu lon"
    )
    assert normalize_question("dthu hnay so vs th trc") == (
        "doanh thu hôm nay so với tháng trước"
    )
    assert normalize_question("giá 50k") == "giá 50k"  # "k" không bị mở rộng
