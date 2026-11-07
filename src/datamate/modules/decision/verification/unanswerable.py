"""Luật "không trả lời được" bằng code (rulebook §7), chạy trước khi gọi LLM.

Chỉ giữ những luật đã đo được độ chính xác cao trên train (scripts/check_unanswerable.py):
câu bị luật bắt sẽ trả unanswerable ngay, không tốn lượt gọi LLM.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from datetime import date

from datamate.core.text import fold
from datamate.modules.data.semantic.capabilities import Capabilities
from datamate.modules.understanding.normalize import time_hints


@dataclass(frozen=True)
class Verdict:
    rule: str
    reason: str


# (tên luật, mẫu câu hỏi đã bỏ dấu, loại thông tin cần có)
_NEEDS: tuple[tuple[str, str, str], ...] = (
    ("no_stock", r"ton kho|trong kho|con ton|\bcon lai\b.*\bkho\b|\bton\b.*cuoi ngay", "stock"),
    ("no_import", r"\bnhap\b|nha cung cap|\bncc\b", "import"),
    ("no_expiry", r"han dung|het han|han su dung|\bhsd\b", "expiry"),
    ("no_gender", r"khach (nu|nam)\b|gioi tinh", "gender"),
    ("no_address", r"dia chi|\bo duong\b|nha o duong|khach o\b", "address"),
    (
        "no_channel",
        r"\bkenh\b|ban qua|qua dien thoai|online|facebook|zalo|shopee|tiktok",
        "channel",
    ),
    ("no_payment", r"\bcod\b|vi dien tu|chuyen khoan|tien mat|thanh toan", "payment"),
    ("no_debt", r"cong no|\bcon no\b|\bno\b|mua chiu|ghi no|thu no|tra no", "debt"),
    (
        "no_customer_group",
        r"nhom khach|khach than thiet|khach vip|khach si\b|khach le\b",
        "customer_group",
    ),
    ("no_staff", r"nhan vien", "staff"),
)
# câu hỏi đánh giá chủ quan: dữ liệu bán hàng không bao giờ trả lời được
_SUBJECTIVE = re.compile(
    r"tan tam|le phep|chu dao|lanh nghe|khen|than thien|nhiet tinh|de thuong|dep trai|xinh"
)


def _outside_data(question: str, today: date, caps: Capabilities) -> Verdict | None:
    if caps.data_start is None or caps.data_end is None:
        return None
    hints = time_hints(question, today)
    if not hints:
        return None
    last = min(caps.data_end, today)
    if all(h.period.end < caps.data_start or h.period.start > last for h in hints):
        span = f"{caps.data_start.isoformat()} → {caps.data_end.isoformat()}"
        return Verdict("outside_data", f"kỳ hỏi nằm ngoài khoảng có dữ liệu ({span})")
    return None


def check_unanswerable(question: str, today: date, caps: Capabilities) -> Verdict | None:
    """Verdict nếu chắc chắn không trả lời được, None nếu không bắt được gì."""
    text = f" {fold(question)} "
    if _SUBJECTIVE.search(text):
        return Verdict("subjective", "câu hỏi đánh giá chủ quan, dữ liệu không ghi")
    for rule, pattern, need in _NEEDS:
        if re.search(pattern, text) and need not in caps.has:
            return Verdict(rule, f"dữ liệu không ghi thông tin '{need}'")
    return _outside_data(question, today, caps)
