"""Nhận biết hình thức thanh toán "ghi nợ" (mua chịu) từ cách ghi tự do (rulebook §2, §4)."""

from __future__ import annotations

from datamate.core.text import fold

# So khớp theo từ nguyên vẹn, như classify_status.
_DEBT_KEYWORDS = ("ghi no", "debt", "cong no", "mua chiu", "tra cham", "no")


def is_debt_payment(value: object) -> bool:
    """Hình thức thanh toán của đơn có phải ghi nợ (khách chưa trả ngay) không."""
    if not isinstance(value, str):
        return False
    text = f" {fold(value).strip()} "
    return any(f" {keyword} " in text for keyword in _DEBT_KEYWORDS)
