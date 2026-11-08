"""Soát kết quả rỗng: "không thể trả lời" hoặc 0 khi câu hỏi đã qua luật "ngoài dữ liệu" của code.

Luật code (``check_unanswerable``) chạy trước vòng lặp; câu nào lọt qua nghĩa là dữ liệu có thể có
thông tin. Khi đó kết quả 0 / rỗng / "không có dữ liệu" thường do bộ lọc sai (tên hàng, nhóm, ngày),
không phải do shop không bán. Check nhắc LLM xem lại MỘT lần; LLM vẫn chắc thì giữ nguyên đáp án.
"""

from __future__ import annotations

from datamate.infrastructure.llm_loop import CheckResult, LoopState
from datamate.modules.domain.answer import Answer, AnswerType, Table

_NAME = "empty_result"
_FEEDBACK = (
    "Kết quả là {what}, trong khi dữ liệu có khoảng thời gian này. Rất có thể BỘ LỌC sai chứ "
    "không phải dữ liệu thiếu. Kiểm tra lại: (1) tên hàng / khách / nhóm: so khớp không phân "
    "biệt hoa thường và dấu, bỏ dấu ngoặc và dấu chấm, hoặc lọc theo từ khoá chính; liệt kê "
    "vài giá trị gần giống (distinct) để chọn đúng tên; (2) khoảng ngày đúng như gợi ý thời "
    "gian; (3) bảng đang dùng có cột cần thiết. Nếu đã kiểm tra mà dữ liệu thật sự không có "
    "thì giữ nguyên đáp án."
)


def _describe(answer: Answer) -> str | None:
    """Mô tả ngắn nếu đáp án rỗng / bằng 0, ngược lại None."""
    if answer.type is AnswerType.UNANSWERABLE:
        return '"không thể trả lời / không có dữ liệu"'
    value = answer.value
    if isinstance(value, bool):
        return None
    if isinstance(value, int | float) and value == 0:
        return "0"
    if isinstance(value, tuple) and not value:
        return "danh sách rỗng"
    if isinstance(value, Table) and not value.rows:
        return "bảng rỗng"
    return None


class EmptyResultCheck:
    """Soát một lần mỗi câu; dùng chung cho mọi bộ giải (kết quả luôn là ``Answer``)."""

    name = _NAME
    kind = "rule"

    def __call__(self, state: LoopState) -> CheckResult | None:
        warned = list(state.get("warned") or [])
        candidate = state["candidate"]
        what = _describe(candidate) if isinstance(candidate, Answer) else None
        if what is None or _NAME in warned:
            return None
        return CheckResult(
            feedback=_FEEDBACK.format(what=what),
            names=[*warned, _NAME],
            trace={"empty": what},
        )
