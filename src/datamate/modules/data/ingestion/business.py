"""Nạp toàn bộ gói dữ liệu một doanh nghiệp thành các bảng sạch có tên."""

from __future__ import annotations

import re
from collections import defaultdict
from dataclasses import dataclass, field
from pathlib import Path

import pandas as pd

from datamate.modules.data.ingestion.columns import type_columns
from datamate.modules.data.ingestion.grouping import fill_group_cells
from datamate.modules.data.ingestion.readers import Part, read_parts, read_sqlite
from datamate.modules.data.ingestion.values import year_in

SOURCE_COLUMN = "_nguon"  # file/sheet gốc của dòng, giúp suy ra năm, tháng
_PART_SUFFIX = re.compile(r"[_\- ]+(\d{1,2}|20\d{2})$")


@dataclass(frozen=True)
class Business:
    """Gói dữ liệu một doanh nghiệp: README và các bảng đã làm sạch."""

    business_id: str
    readme: str
    tables: dict[str, pd.DataFrame]
    filled_columns: dict[str, list[str]] = field(default_factory=dict)


def _group_key(part: Part) -> tuple[str, tuple[str, ...]]:
    return _PART_SUFFIX.sub("", part.base_name), tuple(sorted(part.frame.columns))


def _merge_parts(parts: list[Part]) -> dict[str, pd.DataFrame]:
    """Gộp các sheet/file cùng tên gốc và cùng bộ cột (vd. mỗi tháng một sheet)."""
    groups: dict[tuple[str, tuple[str, ...]], list[Part]] = defaultdict(list)
    for part in parts:
        groups[_group_key(part)].append(part)

    tables: dict[str, pd.DataFrame] = {}
    for (base, _), members in groups.items():
        frames = [m.frame.assign(**{SOURCE_COLUMN: m.source}) for m in members]
        name = base
        if name in tables:  # cùng tên gốc nhưng khác cấu trúc → phân biệt bằng sheet
            name = f"{base}|{members[0].source.split('|')[-1]}"
        tables[name] = pd.concat(frames, ignore_index=True)
    return tables


def _clean(table: pd.DataFrame) -> tuple[pd.DataFrame, list[str]]:
    default_year = table[SOURCE_COLUMN].map(year_in) if SOURCE_COLUMN in table.columns else None
    typed = type_columns(table, default_year)
    return fill_group_cells(typed)


def load_business(directory: Path) -> Business:
    """Nạp mọi file trong thư mục doanh nghiệp thành các bảng sạch có tên."""
    readme_path = directory / "README.md"
    readme = readme_path.read_text(encoding="utf-8") if readme_path.exists() else ""

    parts: list[Part] = []
    raw_tables: dict[str, pd.DataFrame] = {}
    for path in sorted(directory.iterdir()):
        if path.suffix == ".sqlite":
            raw_tables.update(read_sqlite(path))
        else:
            parts.extend(read_parts(path))
    raw_tables.update(_merge_parts(parts))

    tables, filled = {}, {}
    for name, table in raw_tables.items():
        tables[name], filled_columns = _clean(table)
        if filled_columns:
            filled[name] = filled_columns
    return Business(directory.name, readme, tables, filled)
