"""Đặc tả định nghĩa nghiệp vụ lấy từ rulebook (đơn nào tính doanh thu, doanh thu đơn ở đâu).

Đặc tả là DỮ LIỆU, không phải code: rulebook đổi thì biên dịch lại (``compile.py``) chứ không sửa
bộ dựng bảng. Giá trị mặc định là định nghĩa của rulebook hiện tại.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import Any

STATUS_LABELS = ("hoan_thanh", "huy", "tra_hang", "dang_giao", "khac")
REVENUE_BASES = ("line_sum", "order_total")


@dataclass(frozen=True, slots=True)
class RuleSpec:
    """Các định nghĩa nghiệp vụ mà bảng chuẩn tắc cần để đánh dấu đơn và tính doanh thu."""

    revenue_statuses: tuple[str, ...] = ("hoan_thanh", "dang_giao")
    partial_return_voids_order: bool = True  # đơn trả một phần vẫn là đơn trả hàng: bỏ cả đơn
    revenue_basis: str = "line_sum"  # tổng thành tiền các dòng; "order_total" = tổng đơn sau giảm
    # Ca làm theo giờ tạo đơn: (tên, giờ bắt đầu, giờ kết thúc không tính); ngoài ca = "ngoài ca"
    shifts: tuple[tuple[str, int, int], ...] = (("sáng", 6, 14), ("chiều", 14, 22))

    def to_dict(self) -> dict[str, Any]:
        return {
            **asdict(self),
            "revenue_statuses": list(self.revenue_statuses),
            "shifts": [list(s) for s in self.shifts],
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> RuleSpec:
        """Đọc đặc tả; giá trị sai kiểu hoặc ngoài tập cho phép gây ValueError."""
        defaults = cls()
        statuses = tuple(data.get("revenue_statuses", defaults.revenue_statuses))
        if not statuses or any(s not in STATUS_LABELS for s in statuses):
            raise ValueError(f"revenue_statuses không hợp lệ: {statuses!r}")
        basis = data.get("revenue_basis", defaults.revenue_basis)
        if basis not in REVENUE_BASES:
            raise ValueError(f"revenue_basis không hợp lệ: {basis!r}")
        voids = data.get("partial_return_voids_order", defaults.partial_return_voids_order)
        if not isinstance(voids, bool):
            raise ValueError(f"partial_return_voids_order phải là true/false: {voids!r}")
        shifts = _parse_shifts(data.get("shifts", defaults.shifts))
        return cls(statuses, voids, basis, shifts)


def _parse_shifts(raw: Any) -> tuple[tuple[str, int, int], ...]:
    shifts = []
    for item in raw:
        name, start, end = item
        if not (isinstance(name, str) and isinstance(start, int) and isinstance(end, int)):
            raise ValueError(f"ca làm không hợp lệ: {item!r}")
        if not 0 <= start < end <= 24:
            raise ValueError(f"giờ của ca không hợp lệ: {item!r}")
        shifts.append((name, start, end))
    return tuple(shifts)


DEFAULT_SPEC = RuleSpec()
