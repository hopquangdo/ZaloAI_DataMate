from datetime import date
from pathlib import Path

import pandas as pd
import pytest

from datamate.modules.data.ingestion import get_business
from datamate.modules.understanding.normalize import (
    EntityIndex,
    normalize_question,
    time_hints,
    understand,
)

TODAY = date(2026, 3, 4)  # thứ Tư
TRAIN = Path("dataset/train/train")


def rendered(question: str) -> list[str]:
    return [hint.render() for hint in time_hints(question, TODAY)]


def test_normalize_expands_abbreviations_only_as_whole_words():
    assert normalize_question("sp  bán dc nhiều nhất") == "sản phẩm bán được nhiều nhất"
    assert normalize_question("giá 50k, spam") == "giá 50k, spam"  # "k"/"spam" không đổi
    assert normalize_question("bữa qua bnhiu") == "bữa qua bao nhiêu"


def test_relative_weeks_and_months():
    assert rendered("sp bán dc nhiều nhất tuần rồi là gì") == [
        "tuần trước/tuần rồi = 2026-02-23 → 2026-03-01 (thứ Hai → Chủ nhật)"
    ]
    assert rendered("Tháng này bán được bao nhiêu") == [
        "tháng này = 2026-03-01 → 2026-03-04 (ngày 1 → hết hôm nay)"
    ]


def test_hints_carry_the_real_dates_not_just_text():
    (hint,) = time_hints("tuần rồi", TODAY)
    assert (hint.period.start, hint.period.end) == (date(2026, 2, 23), date(2026, 3, 1))
    assert rendered("hôm nay")[0] == "hôm nay = 2026-03-04"
    assert rendered("hôm qua")[0] == "hôm qua = 2026-03-03"


def test_this_month_compared_adds_same_length_previous_period():
    assert any(
        "2026-02-01 → 2026-02-04" in h for h in rendered("doanh thu tháng này so với tháng trước")
    )


def test_month_without_year_goes_to_previous_year_when_after_today():
    assert rendered("tháng 4")[0].endswith("2025-04-01 → 2025-04-30")
    assert rendered("tháng 2")[0].endswith("2026-02-01 → 2026-02-28")
    assert rendered("thang 4/2026")[0].endswith("2026-04-01 → 2026-04-30")


def test_last_n_days_and_quarter():
    assert "2026-02-26 → 2026-03-04" in rendered("7 ngày gần nhất")[0]
    assert rendered("quý 1")[0] == "quý 1/2026 = 2026-01-01 → 2026-03-31"


def test_no_time_phrase_gives_no_hint():
    assert time_hints("mặt hàng nào bán chạy nhất", TODAY) == []


@pytest.mark.skipif(not TRAIN.exists(), reason="chưa có dataset")
def test_entities_match_real_values_ignoring_accents_and_case():
    business = get_business(TRAIN / "data" / "biz_118", Path(".cache/businesses"))
    index = EntityIndex(business)
    name = next(
        v
        for t in business.tables.values()
        for c in t.columns
        if "tên hàng" in str(c).lower() and pd.api.types.is_string_dtype(t[c])
        for v in t[c].dropna().astype(str)
        if len(v) > 8
    )
    lowered = name.lower()
    hits = index.find(f"doanh thu của {lowered} tuần rồi")
    assert any(name in h.values for h in hits)
    result = understand(f"dthu {lowered} tuần rồi", TODAY, index)
    text = result.render(f"dthu {lowered} tuần rồi")
    assert "doanh thu" in text and "Tên trong dữ liệu" in text
