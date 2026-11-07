"""Khớp cụm từ trong câu hỏi với giá trị thật trong dữ liệu (tên hàng, khách, nhóm...).

Lập chỉ mục một lần cho mỗi doanh nghiệp: từ khoá không dấu -> các cách viết gốc ở bảng/cột nào.
Cho LLM biết tên đúng để nó dùng NGUYÊN văn từ dữ liệu thay vì tự gõ lại.
"""

from __future__ import annotations

import difflib
import re
from dataclasses import dataclass

import pandas as pd

from datamate.core.text import fold
from datamate.modules.data.ingestion import SOURCE_COLUMN, Business

_MAX_DISTINCT = 3000  # cột nhiều giá trị hơn thường là mã đơn/mã dòng, không phải thực thể
_MIN_KEY_CHARS = 4
_MAX_NGRAM = 12
_MAX_HITS = 8
_FUZZY_CUTOFF = 0.88  # gõ sai nhẹ: "panadol exta" ≈ "panadol extra"
_FUZZY_MIN_CHARS = 8
_ID_COLUMN = re.compile(r"\bmã (đơn|lô|phiếu|giao dịch|dòng)\b", re.IGNORECASE)


@dataclass(frozen=True)
class EntityHit:
    """Một cụm trong câu hỏi trùng với giá trị trong dữ liệu."""

    phrase: str  # cụm trong câu hỏi (không dấu)
    table: str
    column: str
    values: tuple[str, ...]  # các cách viết gốc trong dữ liệu


def _words(text: str) -> list[str]:
    return re.findall(r"\w+", fold(text))


class EntityIndex:
    """Chỉ mục các giá trị chuỗi của một doanh nghiệp, tra theo từ khoá không dấu."""

    def __init__(self, business: Business) -> None:
        # từ khoá -> {(bảng, cột): {cách viết gốc}}
        self._index: dict[str, dict[tuple[str, str], set[str]]] = {}
        for name, table in business.tables.items():
            for column in table.columns:
                if column == SOURCE_COLUMN or _ID_COLUMN.search(str(column)):
                    continue
                self._add_column(name, str(column), table[column])

    def _add_column(self, table: str, column: str, series: pd.Series) -> None:
        if not (pd.api.types.is_string_dtype(series) or series.dtype == object):
            return
        values = series.dropna().astype(str).unique()
        if len(values) > _MAX_DISTINCT:
            return
        for value in values:
            key = " ".join(_words(value))
            if len(key) >= _MIN_KEY_CHARS and not key.replace(" ", "").isdigit():
                self._index.setdefault(key, {}).setdefault((table, column), set()).add(value)

    def find(self, question: str) -> list[EntityHit]:
        """Các cụm dài nhất trong câu hỏi khớp với giá trị trong dữ liệu (không chồng lấn).

        Mỗi độ dài cụm (dài trước) thử khớp chính xác rồi khớp gần đúng (tên gõ sai nhẹ), để
        một từ đơn như "viên" không chặn mất cả tên hàng dài chứa nó.
        """
        words = _words(question)
        hits: list[EntityHit] = []
        used = [False] * len(words)
        by_size: dict[int, list[str]] = {}
        for key in self._index:
            by_size.setdefault(key.count(" ") + 1, []).append(key)
        for size in range(min(_MAX_NGRAM, len(words)), 0, -1):
            for fuzzy in (False, True):
                if fuzzy and size < 2:
                    continue
                for start in range(len(words) - size + 1):
                    if any(used[start : start + size]):
                        continue
                    phrase = " ".join(words[start : start + size])
                    key = self._match(phrase, by_size.get(size, []), fuzzy=fuzzy)
                    if key is None:
                        continue
                    for i in range(start, start + size):
                        used[i] = True
                    for (table, column), values in sorted(self._index[key].items()):
                        hits.append(EntityHit(phrase, table, column, tuple(sorted(values))[:4]))
        return hits[:_MAX_HITS]

    def _match(self, phrase: str, candidates: list[str], *, fuzzy: bool) -> str | None:
        if not fuzzy:
            return phrase if phrase in self._index else None
        if len(phrase) < _FUZZY_MIN_CHARS:
            return None
        close = difflib.get_close_matches(phrase, candidates, 1, _FUZZY_CUTOFF)
        return close[0] if close else None
