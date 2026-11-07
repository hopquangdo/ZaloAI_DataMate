"""Đọc file thô của một doanh nghiệp: csv, xlsx (mỗi sheet một phần), sqlite."""

from __future__ import annotations

import sqlite3
import warnings
from dataclasses import dataclass
from pathlib import Path

import pandas as pd

from datamate.modules.data.ingestion.header import apply_header


@dataclass
class Part:
    """Một file hoặc sheet đã đọc: tên gốc, nguồn và bảng."""

    base_name: str
    source: str
    frame: pd.DataFrame  # đã có header, chưa đặt kiểu


def read_parts(path: Path) -> list[Part]:
    """Đọc csv/xlsx thành các phần (mỗi sheet một phần); định dạng khác bị bỏ qua."""
    stem = path.stem
    if path.suffix == ".csv":
        raw = pd.read_csv(path, header=None, dtype=str, keep_default_na=True, encoding="utf-8-sig")
        return [Part(stem, path.name, apply_header(raw))]
    if path.suffix == ".xlsx":
        with warnings.catch_warnings():
            warnings.simplefilter("ignore")
            sheets = pd.read_excel(
                path, sheet_name=None, header=None, dtype=object, engine="calamine"
            )
        return [
            Part(stem, f"{path.name}|{sheet}", apply_header(raw)) for sheet, raw in sheets.items()
        ]
    return []


def read_sqlite(path: Path) -> dict[str, pd.DataFrame]:
    """Đọc mọi bảng của file sqlite ở chế độ chỉ đọc."""
    with sqlite3.connect(f"file:{path}?mode=ro", uri=True) as connection:
        names = [
            row[0]
            for row in connection.execute("SELECT name FROM sqlite_master WHERE type='table'")
        ]
        return {name: pd.read_sql_query(f'SELECT * FROM "{name}"', connection) for name in names}
