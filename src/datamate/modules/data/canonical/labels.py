"""Gán nhãn chuẩn cho các cách ghi trạng thái đơn mà code không nhận ra (một lần mỗi doanh nghiệp).

Rulebook: mỗi đơn có đúng một trong bốn trạng thái (hoàn thành, huỷ, trả hàng, đang giao). Code
nhận ra các cách ghi quen; giá trị lạ (tiếng Anh, viết tắt, cách nói riêng của shop) được hỏi LLM
MỘT lần, kết quả lưu ra file để mọi câu hỏi của doanh nghiệp dùng chung và người đọc kiểm tra được.
"""

from __future__ import annotations

import json
import re
from collections.abc import Callable
from pathlib import Path

import pandas as pd

from datamate.modules.data.semantic import column_roles
from datamate.modules.domain.business_rules import classify_status

LABELS = ("hoan_thanh", "huy", "tra_hang", "dang_giao")
_JSON = re.compile(r"\{.*\}", re.DOTALL)

Labeler = Callable[[list[str]], dict[str, str]]


def status_values(tables: dict[str, pd.DataFrame]) -> list[str]:
    """Mọi giá trị (khác nhau) của các cột trạng thái đơn trong dữ liệu."""
    values: set[str] = set()
    for table in tables.values():
        for column, hint in column_roles(table).items():
            if hint.role == "status":
                values.update(str(v) for v in table[column].dropna().unique())
    return sorted(values)


def unknown_status_values(tables: dict[str, pd.DataFrame]) -> list[str]:
    """Giá trị trạng thái code không xếp được vào bốn nhãn chuẩn."""
    return [v for v in status_values(tables) if classify_status(v) not in LABELS]


def parse_labels(text: str, values: list[str]) -> dict[str, str]:
    """Đọc JSON {giá trị: nhãn} từ câu trả lời; bỏ giá trị lạ hoặc nhãn ngoài bốn nhãn chuẩn."""
    match = _JSON.search(text)
    if match is None:
        return {}
    try:
        data = json.loads(match.group(0))
    except json.JSONDecodeError:
        return {}
    wanted = set(values)
    return {
        str(k): str(v) for k, v in data.items() if str(k) in wanted and str(v) in LABELS
    }


def cached_labels(path: Path, values: list[str], labeler: Labeler) -> dict[str, str]:
    """Nhãn cho ``values``: đọc file đã lưu, chỉ hỏi ``labeler`` cho giá trị chưa có."""
    known: dict[str, str] = {}
    if path.exists():
        known = json.loads(path.read_text(encoding="utf-8"))
    missing = [v for v in values if v not in known]
    if missing:
        known.update(labeler(missing))
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(known, ensure_ascii=False, indent=1), encoding="utf-8")
    return {v: known[v] for v in values if v in known}
