from datetime import date

from datamate.modules.understanding.normalize import time_hints

TODAY = date(2026, 5, 11)


def spans(question: str) -> list[tuple[date, date]]:
    return [(h.period.start, h.period.end) for h in time_hints(question, TODAY)]


def test_range_up_to_today_is_one_period() -> None:
    assert spans("Từ 1/1 năm nay đến hết hôm nay bán bao nhiêu đơn") == [(date(2026, 1, 1), TODAY)]


def test_range_between_two_dates() -> None:
    assert spans("từ 23/07/2025 đến hết 29/07/2025 bao nhiêu hàng ế") == [
        (date(2025, 7, 23), date(2025, 7, 29))
    ]


def test_single_date() -> None:
    assert spans("ngày 25/09/2025 bán Kẹo giá bao nhiêu") == [
        (date(2025, 9, 25), date(2025, 9, 25))
    ]


def test_year_to_date_does_not_add_a_separate_today_hint() -> None:
    assert spans("Doanh thu từ đầu năm tới hết hnay") == [(date(2026, 1, 1), TODAY)]
