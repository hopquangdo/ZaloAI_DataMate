"""Điền xuống các ô trống của nhóm dòng (nhiều dòng chi tiết của cùng một đơn, rulebook §8)."""

from __future__ import annotations

import re

import pandas as pd

from datamate.modules.data.ingestion.columns import column_words

_GROUP_FILL_AGREEMENT = 0.95
_GROUP_KEY_NAME = re.compile(
    r"ma (don|hoa don|phieu|chung tu|gd|giao dich|bill)"
    r"|so (phieu|ct|chung tu|hoa don)|hoa don|ma don"
)


def _group_key(table: pd.DataFrame) -> str | None:
    for name in table.columns:
        null_ratio = table[name].isna().mean()
        if _GROUP_KEY_NAME.search(column_words(str(name))) and 0.02 < null_ratio < 0.95:
            return str(name)
    return None


def fill_group_cells(table: pd.DataFrame) -> tuple[pd.DataFrame, list[str]]:
    """Điền xuống các cột cấp đơn bị để trống ở dòng sau của cùng một đơn.

    Cột được điền khi nó trống đúng ở những dòng mà mã đơn trống (≥95% trùng khớp).
    Trả về bảng mới và danh sách cột đã điền.
    """
    key = _group_key(table)
    if key is None:
        return table, []
    key_missing = table[key].isna()
    filled = [key]
    for name in table.columns:
        if name == key:
            continue
        agreement = (table[name].isna() == key_missing).mean()
        if agreement >= _GROUP_FILL_AGREEMENT and table[name].isna().any():
            filled.append(str(name))
    result = table.copy()
    result[filled] = result[filled].ffill()
    return result, filled
