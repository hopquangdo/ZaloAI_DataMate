"""Soát code dùng bảng đã lọc cờ doanh thu mà lại đi lọc đơn huỷ / trả hàng.

Bảng ``don_tinh_doanh_thu`` / ``dong_hang_tinh_doanh_thu`` đã bỏ đơn huỷ và đơn trả, nên đếm đơn
huỷ hay tính tỉ lệ huỷ trên đó luôn ra 0 (hoặc sai). Check nhắc LLM dùng bảng đầy đủ MỘT lần;
luật chỉ nhìn code (không đoán đáp án) và dùng chung cho mọi bộ giải.
"""

from __future__ import annotations

import re

from datamate.infrastructure.llm_loop import CheckResult, LoopState
from datamate.modules.data.canonical import LINES, ORDERS, VIEW_LINES, VIEW_ORDERS

_NAME = "view_misuse"
_VIEWS = (VIEW_ORDERS, VIEW_LINES)
_CANCEL = re.compile(r"""['"](huy|tra_hang)['"]""")
_FEEDBACK = (
    "Code dùng bảng đã lọc ({view}) nhưng lại lọc đơn huỷ / trả hàng. Bảng này ĐÃ LOẠI đơn huỷ và "
    "đơn trả nên không còn đơn nào như vậy. Với số đơn huỷ, đơn trả, tỉ lệ huỷ / trả: dùng bảng "
    f"đầy đủ ({ORDERS} hoặc {LINES}) rồi lọc cột \"Trạng thái chuẩn\"."
)


class ViewMisuseCheck:
    """Nhắc một lần mỗi câu; kết quả vẫn được giữ nếu LLM thấy không cần đổi."""

    name = _NAME
    kind = "rule"

    def __call__(self, state: LoopState) -> CheckResult | None:
        warned = list(state.get("warned") or [])
        code = state.get("code") or ""
        view = next((v for v in _VIEWS if v in code), None)
        if view is None or _NAME in warned or not _CANCEL.search(code):
            return None
        return CheckResult(
            feedback=_FEEDBACK.format(view=view),
            names=[*warned, _NAME],
            trace={"view": view},
        )
