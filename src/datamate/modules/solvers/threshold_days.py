"""Soát code đếm số NGÀY đạt ngưỡng doanh thu mà lại so ngưỡng trên từng đơn / dòng.

"Có bao nhiêu ngày doanh thu từ X trở lên" phải cộng doanh thu theo ngày rồi mới so với X. Lỗi hay
gặp: lọc ``"Doanh thu đơn" >= X`` ngay trên từng đơn rồi đếm ngày khác nhau (ra 0 hoặc sai).
Check chỉ nhìn code, nhắc MỘT lần, dùng chung cho mọi bộ giải.
"""

from __future__ import annotations

import re

from datamate.infrastructure.llm_loop import CheckResult, LoopState

_NAME = "threshold_days"
_COUNTS_DAYS = re.compile(
    r"COUNT\s*\(\s*DISTINCT\s+CAST\([^)]*AS\s+DATE\)|\.dt\.date\.nunique\(|\.dt\.normalize\(\)\.nunique\(",
    re.IGNORECASE,
)
_ROW_THRESHOLD = re.compile(
    r"""["'](?:Doanh thu đơn|Thành tiền dòng|Tổng đơn)["']\]?\s*(?:>=|>)\s*[\d_.]{6,}""",
    re.IGNORECASE,
)
_AGGREGATED = re.compile(r"HAVING|groupby|GROUP\s+BY", re.IGNORECASE)
_FEEDBACK = (
    "Câu hỏi đếm số NGÀY đạt ngưỡng doanh thu: phải CỘNG doanh thu theo từng ngày trước, "
    "rồi mới so với ngưỡng và đếm ngày. Code của bạn đang so ngưỡng trên từng đơn / dòng. Dùng: "
    "SQL: GROUP BY ngày HAVING SUM(\"Doanh thu đơn\") >= X; pandas: "
    "d.groupby(d[\"Ngày đặt\"].dt.date)[\"Doanh thu đơn\"].sum() >= X."
)


class ThresholdDaysCheck:
    """Nhắc một lần mỗi câu."""

    name = _NAME
    kind = "rule"

    def __call__(self, state: LoopState) -> CheckResult | None:
        warned = list(state.get("warned") or [])
        code = state.get("code") or ""
        if _NAME in warned or not _COUNTS_DAYS.search(code) or not _ROW_THRESHOLD.search(code):
            return None
        if _AGGREGATED.search(code):  # đã gom theo ngày: bỏ qua
            return None
        return CheckResult(feedback=_FEEDBACK, names=[*warned, _NAME], trace={"rule": _NAME})
