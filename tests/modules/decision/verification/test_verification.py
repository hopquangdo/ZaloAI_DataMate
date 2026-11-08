from datetime import date

from datamate.modules.data.semantic.capabilities import Capabilities
from datamate.modules.decision.verification import check_answer, check_unanswerable
from datamate.modules.domain.answer import Answer, AnswerType

TODAY = date(2026, 3, 4)
CAPS = Capabilities(
    has=frozenset({"customer", "status", "payment"}),
    data_start=date(2025, 6, 1),
    data_end=date(2026, 3, 4),
)


def rule(question: str) -> str | None:
    verdict = check_unanswerable(question, TODAY, CAPS)
    return None if verdict is None else verdict.rule


def test_period_entirely_before_data_is_unanswerable() -> None:
    assert rule("doanh thu tháng 2/2025 là bao nhiêu") == "outside_data"
    assert rule("doanh thu tháng 2/2026 là bao nhiêu") is None


def test_information_the_shop_does_not_record() -> None:
    assert rule("hết hôm nay trong kho còn bao nhiêu hộp sữa") == "no_stock"
    assert rule("khách nữ chiếm bao nhiêu % doanh thu") == "no_gender"
    assert rule("tổng tiền nhập hàng tháng này") == "no_import"
    assert rule("doanh thu đơn COD tháng này") is None  # shop có ghi hình thức thanh toán


def test_subjective_questions_are_never_answerable() -> None:
    assert rule("nhân viên nào tận tâm với khách nhất") == "subjective"


def test_ordinary_question_is_left_to_the_solvers() -> None:
    assert rule("tháng này bán được bao nhiêu tiền") is None


NAMES = frozenset({"cà phê sữa", "trà đào", "cao long minh 0321806537"})


def test_name_must_exist_in_data() -> None:
    assert check_answer(Answer(AnswerType.STRING, "Cà phê sữa"), NAMES) is None
    assert check_answer(Answer(AnswerType.STRING, "Cao Long Minh"), NAMES) is None  # chứa trọn từ
    assert check_answer(Answer(AnswerType.STRING, "Bánh mì"), NAMES) is not None
    assert check_answer(Answer(AnswerType.STRING, "Thứ Hai"), NAMES) is None  # tên thứ trong tuần
    assert check_answer(Answer(AnswerType.LIST, ("Trà đào", "Bánh mì")), NAMES) is not None


def test_numbers_pass_and_absurd_percent_fails() -> None:
    assert check_answer(Answer(AnswerType.NUMBER, 12345), NAMES) is None
    assert check_answer(Answer(AnswerType.PERCENT, 1e9), NAMES) is not None


def test_walk_in_customer_is_never_an_answer() -> None:
    walk_in = frozenset({"khách lẻ", "nguyễn văn a"})
    assert check_answer(Answer(AnswerType.STRING, "Khách lẻ"), walk_in) is not None
    assert check_answer(Answer(AnswerType.LIST, ("Nguyễn Văn A", "khách vãng lai")), walk_in) is not None
    assert check_answer(Answer(AnswerType.STRING, "Nguyễn Văn A"), walk_in) is None
    assert check_answer(Answer(AnswerType.STRING, "lẻ"), frozenset({"lẻ"})) is None  # tên nhóm khách
