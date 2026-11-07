"""Quy đổi cách nói thời gian tương đối trong câu hỏi thành khoảng ngày cụ thể (rulebook §2).

Chỉ đưa ra gợi ý bằng code; LLM vẫn có thể dùng module ``P`` để tự tính nếu cần.
"""

from __future__ import annotations

import re
from collections.abc import Callable
from dataclasses import dataclass
from datetime import date, timedelta

from datamate.core.text import fold
from datamate.modules.domain.periods import Period, period

_MAX_DAYS = 3660
_DAY_COUNT = re.compile(r"(\d+) ngay (?:gan nhat|qua|vua qua|gan day)")
_MONTH = re.compile(r"thang (\d{1,2})(?: ?[/-] ?(\d{4})| nam (\d{4}))?(?!\d)")
_QUARTER = re.compile(r"quy (\d)(?: ?[/-]? ?(?:nam )?(\d{4}))?")


@dataclass(frozen=True, slots=True)
class TimeHint:
    """Một cách nói thời gian trong câu hỏi và khoảng ngày nó có nghĩa."""

    label: str
    period: Period
    note: str = ""

    def render(self) -> str:
        start, end = self.period.start.isoformat(), self.period.end.isoformat()
        span = start if start == end else f"{start} → {end}"
        text = f"{self.label} = {span}"
        return f"{text} {self.note}" if self.note else text


def _has(text: str, *phrases: str) -> bool:
    return any(f" {phrase} " in text for phrase in phrases)


# Mỗi luật: (một trong các cụm, cụm đi kèm bắt buộc, hàm tạo gợi ý từ "hôm nay").
_PHRASE_RULES: tuple[tuple[tuple[str, ...], tuple[str, ...], Callable[[date], TimeHint]], ...] = (
    (("hom nay",), (), lambda t: TimeHint("hôm nay", period.day(t))),
    (
        ("hom qua", "bua qua", "hom wa"),
        (),
        lambda t: TimeHint("hôm qua", period.day(t - timedelta(days=1))),
    ),
    (
        ("tuan nay",),
        (),
        lambda t: TimeHint("tuần này", period.this_week(t), "(thứ Hai → hết hôm nay)"),
    ),
    (
        ("tuan truoc", "tuan roi", "tuan qua"),
        (),
        lambda t: TimeHint("tuần trước/tuần rồi", period.last_week(t), "(thứ Hai → Chủ nhật)"),
    ),
    (
        ("thang nay",),
        (),
        lambda t: TimeHint("tháng này", period.this_month(t), "(ngày 1 → hết hôm nay)"),
    ),
    (
        ("thang nay",),
        ("so voi",),
        lambda t: TimeHint(
            "tháng trước cùng số ngày (để so với tháng này)", period.last_month_same_days(t)
        ),
    ),
    (
        ("thang truoc", "thang roi", "thang qua"),
        (),
        lambda t: TimeHint("tháng trước", period.previous_month(t.year, t.month)),
    ),
    (("tu dau nam",), (), lambda t: TimeHint("từ đầu năm", period.year_to_date(t))),
)


def _phrase_hints(text: str, today: date) -> list[TimeHint]:
    return [
        build(today)
        for any_of, also, build in _PHRASE_RULES
        if _has(text, *any_of) and (not also or _has(text, *also))
    ]


def _day_count_hints(text: str, today: date) -> list[TimeHint]:
    hints = []
    for match in _DAY_COUNT.finditer(text):
        n = int(match.group(1))
        if 0 < n <= _MAX_DAYS:
            hints.append(
                TimeHint(f"{n} ngày gần nhất", period.last_n_days(today, n), "(kể cả hôm nay)")
            )
    return hints


def _month_hints(text: str, today: date) -> list[TimeHint]:
    hints = []
    for match in _MONTH.finditer(text):
        month = int(match.group(1))
        if not 1 <= month <= 12:
            continue
        year = match.group(2) or match.group(3)
        if year:
            hints.append(TimeHint(f"tháng {month}/{year}", period.month(int(year), month)))
        else:
            inferred = period.year_of_month(month, today)
            hints.append(TimeHint(f"tháng {month} (không ghi năm)", period.month(inferred, month)))
    return hints


def _quarter_hints(text: str, today: date) -> list[TimeHint]:
    hints = []
    for match in _QUARTER.finditer(text):
        quarter = int(match.group(1))
        if not 1 <= quarter <= 4:
            continue
        year = (
            int(match.group(2)) if match.group(2) else period.year_of_month(quarter * 3 - 2, today)
        )
        hints.append(TimeHint(f"quý {quarter}/{year}", period.quarter(year, quarter)))
    return hints


def time_hints(question: str, today: date) -> list[TimeHint]:
    """Các cách nói thời gian tìm thấy trong câu hỏi, không trùng lặp, giữ thứ tự."""
    text = f" {fold(question)} "
    hints = [
        *_phrase_hints(text, today),
        *_day_count_hints(text, today),
        *_month_hints(text, today),
        *_quarter_hints(text, today),
    ]
    return list(dict.fromkeys(hints))
