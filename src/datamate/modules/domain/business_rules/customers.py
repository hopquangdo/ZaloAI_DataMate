"""Khách lẻ / vãng lai không phải một khách (rulebook §3): không đếm, không xếp hạng."""

from __future__ import annotations

from datamate.core.text import normalize_text

# Không đưa "lẻ" trơn vào đây vì đó có thể là tên một nhóm khách hợp lệ (rulebook §1).
_WALK_IN = frozenset(
    normalize_text(name)
    for name in ("Khách lẻ", "Khách vãng lai", "Khách hàng lẻ", "KL", "Vãng lai")
)


def is_walk_in(value: object) -> bool:
    """Tên khách ghi trên đơn có phải khách lẻ / vãng lai không."""
    return isinstance(value, str) and normalize_text(value) in _WALK_IN
