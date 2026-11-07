import pandas as pd

from datamate.modules.data.ingestion import Business
from datamate.modules.data.profiling import describe_business


def test_describes_each_column_kind() -> None:
    table = pd.DataFrame(
        {
            "ngay": pd.to_datetime(["2025-01-01", "2025-01-02"]),
            "tien": [1.0, 2.5],
            "ten": ["An", "Bình"],
            "ghi_chu": [None, "x"],
        }
    )
    text = describe_business(Business("biz", "", {"don": table}))
    assert 'T["don"] — 2 dòng' in text
    assert "date 2025-01-01 → 2025-01-02" in text
    assert "số 1 → 2.5" in text
    assert "chữ, 2 giá trị" in text
    assert "trống 50%" in text


def test_long_text_columns_show_only_examples() -> None:
    names = [f"khách {i}" for i in range(40)]
    text = describe_business(Business("biz", "", {"kh": pd.DataFrame({"ten": names})}))
    assert "40 giá trị khác nhau" in text
    assert "khách 39" not in text
