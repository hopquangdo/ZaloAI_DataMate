"""assets/prompts/toolkit.md phải mô tả đúng những tên mà build_namespace cung cấp."""

from __future__ import annotations

import re
from datetime import date
from typing import Any

import pandas as pd

from datamate.infrastructure.prompt_loader import load_prompt
from datamate.modules.data.ingestion import Business
from datamate.modules.domain.periods import LunarCalendar, period
from datamate.modules.solvers.pandas.toolkit import build_namespace


def _namespace() -> dict[str, Any]:
    return build_namespace(Business("x", "", {}), date(2026, 3, 4), LunarCalendar(pd.DataFrame()))


def test_every_namespace_name_is_documented() -> None:
    doc = load_prompt("toolkit")
    missing = [
        name for name in _namespace() if not re.search(rf"(?<!\w){re.escape(name)}(?!\w)", doc)
    ]
    assert missing == []


def test_p_exposes_exactly_the_documented_period_api() -> None:
    exposed = set(vars(_namespace()["P"]))
    # không lộ pd, date, dataclass… của period.py; chỉ thêm hai tên model hay tự nghĩ ra
    aliases = {"week", "previous_week", "date", "last_month", "range", "span"}
    assert exposed == set(period.__all__) | {"previous_day", "yesterday"} | aliases
    doc = load_prompt("toolkit")
    assert [name for name in sorted(exposed - aliases) if f"P.{name}" not in doc] == []
