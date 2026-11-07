"""Tri thức dùng chung cho mọi doanh nghiệp trong một tập: rulebook và lịch âm–dương.

Nạp từ thư mục của tập (train / public_test / ...), nên thuộc về cách bố trí dữ liệu của app.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from datamate.modules.domain.periods import LunarCalendar

RULEBOOK_FILE = "rulebook.md"
CALENDAR_FILE = "calendar.csv"


@dataclass(frozen=True)
class Knowledge:
    """Rulebook và lịch âm–dương dùng chung cho cả tập."""

    rulebook: str
    lunar: LunarCalendar


def load_knowledge(split_dir: Path) -> Knowledge:
    """Đọc tri thức dùng chung. Thiếu file thì báo rõ tên file thay vì lỗi mơ hồ phía sau."""
    rulebook_path, calendar_path = split_dir / RULEBOOK_FILE, split_dir / CALENDAR_FILE
    for path in (rulebook_path, calendar_path):
        if not path.exists():
            raise FileNotFoundError(f"Thiếu {path.name} trong {split_dir}")
    return Knowledge(
        rulebook=rulebook_path.read_text(encoding="utf-8"),
        lunar=LunarCalendar.load(calendar_path),
    )
