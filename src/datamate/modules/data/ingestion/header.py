"""Dò dòng tiêu đề của bảng thô (bỏ tiêu đề báo cáo, bộ lọc phía trên) và đặt tên cột."""

from __future__ import annotations

from typing import Any

import pandas as pd

from datamate.modules.data.ingestion.values import parse_number

_HEADER_SCAN_ROWS = 12


def _is_label(value: Any) -> bool:
    return isinstance(value, str) and bool(value.strip()) and parse_number(value) is None


def _header_row(raw: pd.DataFrame) -> int:
    """Dòng đầu tiên phủ nhiều cột nhất mà toàn là nhãn chữ (bỏ tiêu đề, bộ lọc phía trên)."""
    best_row, best_coverage = 0, -1
    for index in range(min(_HEADER_SCAN_ROWS, len(raw))):
        cells = [v for v in raw.iloc[index].tolist() if not pd.isna(v)]
        if cells and all(_is_label(v) for v in cells) and len(cells) > best_coverage:
            best_row, best_coverage = index, len(cells)
    return best_row


def _unique_names(names: list[Any]) -> list[str]:
    seen: dict[str, int] = {}
    result = []
    for position, name in enumerate(names):
        label = str(name).strip() if not pd.isna(name) and str(name).strip() else f"col_{position}"
        seen[label] = seen.get(label, 0) + 1
        result.append(label if seen[label] == 1 else f"{label}_{seen[label]}")
    return result


def apply_header(raw: pd.DataFrame) -> pd.DataFrame:
    """Đặt dòng tiêu đề làm tên cột (không trùng) và bỏ dòng/cột trống hoàn toàn."""
    row = _header_row(raw)
    table: pd.DataFrame = raw.iloc[row + 1 :].copy()
    table.columns = _unique_names(raw.iloc[row].tolist())
    table = table.dropna(how="all").dropna(axis=1, how="all")
    cleaned: pd.DataFrame = table.reset_index(drop=True)
    return cleaned
