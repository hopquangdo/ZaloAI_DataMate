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
_MONTH = re.compile(r"thang (\d{1,2})(?: ?[/-] ?(\d{4}|\d{2})| nam (\d{4}))?(?!\d)")
# "3/25", "4/2025" (không có chữ "tháng"): tháng/năm. Số sau là năm 2 chữ số (13-99) hoặc 4 chữ số;
# tránh nhầm với ngày/tháng ("28/5") và với ngày đủ ba phần ("29/06/2025").
_BARE_MONTH = re.compile(r"(?<![\d/])(\d{1,2})/(20\d{2}|[1-9]\d)(?![\d/])")
_QUARTER = re.compile(r"quy (\d)(?: ?[/-]? ?(?:nam )?(\d{4}))?")
_DATE = r"(\d{1,2})[/-](\d{1,2})(?:[/-](\d{4})| nam (\d{4}|nay))?"
_TODAY_WORDS = r"(?:het )?(?:hom nay|hnay|bua nay|ngay hom nay|bay gio)"
_RANGE = re.compile(
    rf"\btu (?:ngay )?{_DATE} (?:den|toi|->|-) (?:het )?(?:ngay )?(?:{_DATE}|{_TODAY_WORDS})"
)
_ON_DATE = re.compile(rf"\bngay {_DATE}")
_ANY_DATE = re.compile(rf"\b{_DATE}")
_WINDOW = re.compile(r"(\d+) ngay (?:ke tu|tinh tu|sau)")


@dataclass(frozen=True, slots=True)
class TimeHint:
    """Một cách nói thời gian trong câu hỏi và khoảng ngày nó có nghĩa."""

    label: str
    period: Period
    note: str = ""

    def render(self) -> str:
        start, end = self.period.start.isoformat(), self.period.end.isoformat()
        span = start if start == end else f"{start} → {end}"
        sql = f"= DATE '{start}'" if start == end else f"BETWEEN DATE '{start}' AND DATE '{end}'"
        pandas = f"P.day('{start}')" if start == end else f"P.between('{start}', '{end}')"
        text = f"{self.label} = {span} (SQL: {sql}; pandas: {pandas})"
        return f"{text} {self.note}" if self.note else text


def _has(text: str, *phrases: str) -> bool:
    return any(f" {phrase} " in text for phrase in phrases)


# Mỗi luật: (một trong các cụm, cụm đi kèm bắt buộc, hàm tạo gợi ý từ "hôm nay").
_PHRASE_RULES: tuple[tuple[tuple[str, ...], tuple[str, ...], Callable[[date], TimeHint]], ...] = (
    (("hom nay", "hnay", "bua nay"), (), lambda t: TimeHint("hôm nay", period.day(t))),
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
            full = 2000 + int(year) if len(year) == 2 else int(year)  # "3/26" = tháng 3/2026
            hints.append(TimeHint(f"tháng {month}/{full}", period.month(full, month)))
        else:
            inferred = period.year_of_month(month, today)
            hints.append(TimeHint(f"tháng {month} (không ghi năm)", period.month(inferred, month)))
    return hints


def _bare_month_hints(text: str) -> list[TimeHint]:
    hints = []
    for match in _BARE_MONTH.finditer(text):
        month, year = int(match.group(1)), match.group(2)
        full = int(year) if len(year) == 4 else 2000 + int(year)
        if 1 <= month <= 12 and (len(year) == 4 or int(year) > 12) and 2000 <= full <= 2100:
            hints.append(TimeHint(f"tháng {month}/{full}", period.month(full, month)))
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


def _as_date(day: str, month: str, year: str | None, today: date) -> date | None:
    year_value = today.year if year in (None, "nay") else int(year)
    try:
        return date(year_value, int(month), int(day))
    except ValueError:
        return None


def _range_hints(text: str, today: date) -> list[TimeHint]:
    """ "từ 1/1 năm nay đến hết hôm nay", "từ 23/07/2025 đến 29/07/2025" → một khoảng ngày."""
    hints = []
    for match in _RANGE.finditer(text):
        start = _as_date(match.group(1), match.group(2), match.group(3) or match.group(4), today)
        if match.group(5):
            end = _as_date(match.group(5), match.group(6), match.group(7) or match.group(8), today)
        else:
            end = today
        if start and end and start <= end:
            hints.append(TimeHint("khoảng ngày nêu trong câu", Period(start, end)))
    return hints


def _date_hints(text: str, today: date) -> list[TimeHint]:
    hints = []
    for match in _ON_DATE.finditer(text):
        day = _as_date(match.group(1), match.group(2), match.group(3) or match.group(4), today)
        if day:
            hints.append(TimeHint(f"ngày {day.isoformat()}", period.day(day)))
    return hints


def _window_hints(text: str, today: date) -> list[TimeHint]:
    """"N ngày kể từ ngày D so với N ngày liền trước" → hai khoảng ngày liền kề quanh ngày D."""
    window, found = _WINDOW.search(text), _ANY_DATE.search(text)
    if window is None or found is None or "truoc" not in text:
        return []
    days = int(window.group(1))
    start = _as_date(found.group(1), found.group(2), found.group(3) or found.group(4), today)
    if start is None or not 0 < days <= _MAX_DAYS:
        return []
    after = Period(start, start + timedelta(days=days - 1))
    before = Period(start - timedelta(days=days), start - timedelta(days=1))
    return [
        TimeHint(f"{days} ngày kể từ ngày {start.isoformat()}", after, "(gồm cả ngày đó)"),
        TimeHint(f"{days} ngày liền trước ngày {start.isoformat()}", before),
    ]


def time_hints(question: str, today: date) -> list[TimeHint]:
    """Các cách nói thời gian tìm thấy trong câu hỏi, không trùng lặp, giữ thứ tự."""
    text = f" {fold(question)} "
    ranges = _range_hints(text, today)
    if ranges:  # "hôm nay", ngày lẻ trong câu chỉ là hai đầu của khoảng: không gợi ý riêng
        return ranges
    hints = [
        *_window_hints(text, today),
        *_date_hints(text, today),
        *_phrase_hints(text, today),
        *_day_count_hints(text, today),
        *_month_hints(text, today),
        *_bare_month_hints(text),
        *_quarter_hints(text, today),
    ]
    if any(h.label == "từ đầu năm" for h in hints):  # "từ đầu năm tới hết hôm nay"
        hints = [h for h in hints if h.label != "hôm nay"]
    return _relative_to_explicit_month(list(dict.fromkeys(hints)))


def _relative_to_explicit_month(hints: list[TimeHint]) -> list[TimeHint]:
    """"Tháng 3/2026 so với tháng trước": "tháng trước" là tháng liền trước tháng 3, không phải
    tháng trước hôm nay."""
    explicit = [h for h in hints if re.fullmatch(r"tháng \d{1,2}/\d{4}", h.label)]
    relative = [h for h in hints if h.label == "tháng trước"]
    if len(explicit) != 1 or not relative:
        return hints
    start = explicit[0].period.start
    before = period.previous_month(start.year, start.month)
    kept = [h for h in hints if h not in relative]
    return [*kept, TimeHint(f"tháng liền trước {explicit[0].label}", before)]
