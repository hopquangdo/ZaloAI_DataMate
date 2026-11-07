from datamate.modules.decision.consensus import signature, vote
from datamate.modules.domain.answer import ABSTAIN, Answer, AnswerType, Table


def num(x: float) -> Answer:
    return Answer(AnswerType.NUMBER, x)


def text(value: str) -> Answer:
    return Answer(AnswerType.STRING, value)


def test_two_of_three_agree_wins():
    assert vote([num(100), num(99), num(100.0)], 2) == num(100)


def test_no_agreement_abstains():
    assert vote([num(1), num(2), num(3)], 2) is None


def test_tie_at_top_abstains():
    assert vote([num(1), num(1), num(2), num(2)], 2) is None


def test_single_sample_with_min_agree_one():
    assert vote([num(5)], 1) == num(5)


def test_abstain_never_votes():
    assert vote([ABSTAIN, ABSTAIN, num(7)], 2) is None
    assert vote([ABSTAIN, ABSTAIN], 1) is None
    assert vote([], 1) is None


def test_strings_compare_after_normalization_keeping_accents():
    a, b, c = text("Sting  Dâu 330ml"), text("sting dâu 330ml!"), text("sting dau 330ml")
    assert signature(a) == signature(b)
    assert signature(a) != signature(c)


def test_list_is_ordered_table_rows_are_a_set():
    ab = Answer(AnswerType.LIST, ("a", "b"))
    ba = Answer(AnswerType.LIST, ("b", "a"))
    assert signature(ab) != signature(ba)
    t1 = Answer(AnswerType.TABLE, Table(("x", "y"), (("a", 1), ("b", 2))))
    t2 = Answer(AnswerType.TABLE, Table(("X", "Y"), (("b", 2), ("a", 1.0))))
    assert signature(t1) == signature(t2)


def test_table_with_mixed_cell_types_in_a_column_does_not_crash():
    mixed = Answer(AnswerType.TABLE, Table(("x",), ((1,), ("a",))))
    assert signature(mixed) is not None


def test_unanswerable_can_win():
    u, v = Answer.unanswerable("a"), Answer.unanswerable("b")
    assert vote([u, v, num(1)], 2) == u


def test_vote_requires_distinct_sources_when_asked() -> None:
    five = Answer(AnswerType.NUMBER, 5)
    seven = Answer(AnswerType.NUMBER, 7)
    same_solver = [five, seven, five]
    assert vote(same_solver, 2, ["pandas", "sql", "pandas"], min_sources=2) is None
    assert vote([five, five], 2, ["pandas", "sql"], min_sources=2) == five
    assert vote(same_solver, 2) == five  # mặc định không đòi nguồn khác nhau
