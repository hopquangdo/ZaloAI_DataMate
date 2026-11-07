"""Mô tả ngắn các bảng đã làm sạch để đưa vào prompt."""

from __future__ import annotations

import pandas as pd

from datamate.modules.data.ingestion import SOURCE_COLUMN, Business
from datamate.modules.data.semantic import column_roles

_MAX_CATEGORIES = 15
_MAX_TEXT_EXAMPLES = 4
_MAX_CELL = 40


def _short(value: object) -> str:
    text = str(value)
    return text if len(text) <= _MAX_CELL else text[: _MAX_CELL - 1] + "…"


def _describe_column(series: pd.Series) -> str:
    present = series.dropna()
    missing = f", trống {series.isna().mean():.0%}" if series.isna().any() else ""
    if present.empty:
        return f"rỗng{missing}"
    if pd.api.types.is_datetime64_any_dtype(series):
        has_time = bool((present.dt.normalize() != present).any())
        kind = "datetime" if has_time else "date"
        return f"{kind} {present.min():%Y-%m-%d} → {present.max():%Y-%m-%d}{missing}"
    if pd.api.types.is_numeric_dtype(series):
        return f"số {present.min():g} → {present.max():g}{missing}"
    counts = present.astype(str).value_counts()
    if len(counts) <= _MAX_CATEGORIES:
        values = ", ".join(f"{_short(v)!r}×{n}" for v, n in counts.items())
        return f"chữ, {len(counts)} giá trị: {values}{missing}"
    examples = ", ".join(repr(_short(v)) for v in counts.index[:_MAX_TEXT_EXAMPLES])
    return f"chữ, {len(counts)} giá trị khác nhau, vd. {examples}{missing}"


def describe_table(name: str, table: pd.DataFrame, filled: list[str]) -> str:
    """Mô tả một bảng: số dòng và từng cột, kèm gợi ý vai trò cột."""
    hints = column_roles(table)
    lines = [f'T["{name}"] — {len(table)} dòng']
    for column in table.columns:
        if column == SOURCE_COLUMN:
            sources = table[column].nunique()
            lines.append(f'  - "{column}": file|sheet gốc ({sources} giá trị)')
            continue
        note = " [đã điền xuống ô trống của nhóm dòng]" if column in filled else ""
        hint = hints.get(str(column))
        if hint is not None:
            note += f" [gợi ý: {hint.label}]"
        lines.append(f'  - "{column}": {_describe_column(table[column])}{note}')
    return "\n".join(lines)


def describe_business(business: Business) -> str:
    """Mô tả mọi bảng của doanh nghiệp để đưa vào prompt."""
    return "\n\n".join(
        describe_table(name, table, business.filled_columns.get(name, []))
        for name, table in business.tables.items()
    )
