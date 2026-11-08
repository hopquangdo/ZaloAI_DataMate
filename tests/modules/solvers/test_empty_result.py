from datamate.modules.domain.answer import Answer, AnswerType, Table
from datamate.modules.solvers.empty_result import EmptyResultCheck


def _state(answer: Answer, warned: list[str] | None = None) -> dict:
    return {"candidate": answer, "warned": warned or []}


def test_zero_and_unanswerable_are_questioned_once() -> None:
    check = EmptyResultCheck()
    zero = check(_state(Answer(AnswerType.NUMBER, 0)))  # type: ignore[arg-type]
    assert zero is not None and zero.rejected
    assert check(_state(Answer.unanswerable("không có"))) is not None  # type: ignore[arg-type]
    assert check(_state(Answer(AnswerType.NUMBER, 0), zero.names)) is None  # type: ignore[arg-type]


def test_real_values_pass() -> None:
    check = EmptyResultCheck()
    assert check(_state(Answer(AnswerType.NUMBER, 12))) is None  # type: ignore[arg-type]
    assert check(_state(Answer(AnswerType.BOOLEAN, False))) is None  # type: ignore[arg-type]
    table = Table(("a",), (("x",),))
    assert check(_state(Answer(AnswerType.TABLE, table))) is None  # type: ignore[arg-type]


def test_empty_list_and_table_are_questioned() -> None:
    check = EmptyResultCheck()
    assert check(_state(Answer(AnswerType.LIST, ()))) is not None  # type: ignore[arg-type]
    assert check(_state(Answer(AnswerType.TABLE, Table(("a",), ())))) is not None  # type: ignore[arg-type]
