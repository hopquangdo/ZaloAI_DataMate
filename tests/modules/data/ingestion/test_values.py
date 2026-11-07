from datetime import datetime

import pytest

from datamate.modules.data.ingestion.values import parse_datetime, parse_number, year_in


@pytest.mark.parametrize(
    ("raw", "expected"),
    [
        ("560,000", 560000),
        ("55.000đ", 55000),
        ("45,000.0000", 45000),
        ("1tr440", 1_440_000),
        ("1,6256tr", 1_625_600),
        ("2tr", 2_000_000),
        ("396k", 396_000),
        ("38.400đ", 38400),
        ("3 chai", 3),
        ("2 thùng", 2),
        ("1.5", 1.5),
        ("-12,5", -12.5),
        (52000, 52000),
        ("abc", None),
        ("2025-01-01 06:03:04", None),
        ("01/01/2025", None),
        (None, None),
        ("", None),
    ],
)
def test_parse_number(raw: object, expected: float | None) -> None:
    assert parse_number(raw) == expected


@pytest.mark.parametrize(
    ("raw", "expected"),
    [
        ("01/04/2025", datetime(2025, 4, 1)),
        ("1 thg 6 2025", datetime(2025, 6, 1)),
        ("2025-02-01 08:15:00", datetime(2025, 2, 1, 8, 15)),
        (45689, datetime(2025, 2, 1)),
        ("45689", datetime(2025, 2, 1)),
        ("31/02/2025", None),
        ("hôm nay", None),
    ],
)
def test_parse_datetime(raw: object, expected: datetime | None) -> None:
    assert parse_datetime(raw) == expected


def test_day_month_without_year_uses_sheet_year() -> None:
    assert parse_datetime("1/1", default_year=2025) == datetime(2025, 1, 1)
    assert parse_datetime("1/1") is None
    assert year_in("Tháng 01-2025") == 2025
    assert year_in("Sheet1") is None
