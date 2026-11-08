"""Namespace mà code của LLM được dùng: bảng, thư viện, helper thời gian và tiền."""

from __future__ import annotations

import math
from datetime import date, datetime, timedelta
from typing import Any

import numpy as np
import pandas as pd

from datamate.core.text import name_key, normalize_text
from datamate.modules.data.ingestion import Business
from datamate.modules.domain.business_rules import order_status, pct, pct_change, round_money
from datamate.modules.domain.periods import LunarCalendar
from datamate.modules.solvers.pandas.sandbox import Unanswerable
from datamate.modules.solvers.pandas.time_tools import LunarTools, PeriodTools


def unanswerable(reason: str) -> None:
    """Gọi khi dữ liệu không đủ để trả lời (rulebook §7)."""
    raise Unanswerable(reason)


def build_namespace(business: Business, today: date, lunar: LunarCalendar) -> dict[str, Any]:
    """Namespace cho code LLM: bảng (bản sao), thư viện, kỳ thời gian, luật nghiệp vụ."""
    return {
        "T": {name: table.copy() for name, table in business.tables.items()},
        "pd": pd,
        "np": np,
        "math": math,
        "date": date,
        "datetime": datetime,
        "timedelta": timedelta,
        "today": pd.Timestamp(today),  # so sánh thẳng được với cột datetime64
        "P": PeriodTools(),
        "lunar": LunarTools(lunar),
        "norm": normalize_text,
        "fold": name_key,  # LLM gọi fold(): bỏ dấu và bỏ dấu câu, để "(M)" khớp "m"
        "order_status": order_status,
        "round_money": round_money,
        "pct": pct,
        "pct_change": pct_change,
        "unanswerable": unanswerable,
    }
