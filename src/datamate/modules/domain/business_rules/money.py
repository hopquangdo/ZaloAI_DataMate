"""Luật tính tiền và phần trăm theo rulebook (§1, §3)."""

from __future__ import annotations

import math


def round_money(value: float) -> int:
    """Làm tròn về đồng, nửa đồng làm tròn lên (rulebook §3)."""
    return math.floor(value + 0.5)


def pct(part: float, whole: float) -> float:
    """part / whole × 100, làm tròn 2 chữ số."""
    if whole == 0:
        raise ZeroDivisionError("mẫu số bằng 0 khi tính phần trăm")
    return round(part / whole * 100, 2)


def pct_change(current: float, previous: float) -> float:
    """% thay đổi so với kỳ trước; giảm ra số âm (rulebook §1)."""
    if previous == 0:
        raise ZeroDivisionError("kỳ so sánh bằng 0, không tính được % thay đổi")
    return round((current - previous) / previous * 100, 2)
