"""Chuẩn hoá câu hỏi đời thường: gộp khoảng trắng, giải mã Telex sót, mở rộng viết tắt.

Từ điển viết tắt ở assets/lexicon/abbreviations.tsv (chỉ những viết tắt không mơ hồ).
Kết quả chỉ dùng làm gợi ý cho LLM; câu hỏi gốc vẫn được gửi nguyên.
"""

from __future__ import annotations

import functools
import re
from pathlib import Path

from datamate.modules.understanding.normalize.telex import decode_word

LEXICON = Path(__file__).resolve().parents[3] / "assets" / "lexicon" / "abbreviations.tsv"
_TOKEN = re.compile(r"\w+|\W+", re.UNICODE)
_MONTH_ABBR = re.compile(r"th\d{1,2}", re.IGNORECASE)


@functools.cache
def abbreviations() -> dict[str, str]:
    table: dict[str, str] = {}
    for line in LEXICON.read_text(encoding="utf-8").splitlines():
        if not line.strip() or line.startswith("#"):
            continue
        short, full, *_ = [*line.split("\t"), ""]
        if short.strip() and full.strip():
            table[short.strip().lower()] = full.strip()
    return table


def normalize_question(text: str) -> str:
    """Câu hỏi đã gộp khoảng trắng, giải mã Telex sót và mở rộng viết tắt (giữ dấu, số, ký hiệu)."""
    table = abbreviations()
    out: list[str] = []
    for token in _TOKEN.findall(" ".join(text.split())):
        if _MONTH_ABBR.fullmatch(token):  # "th8" = "tháng 8"
            out.append(f"tháng {token[2:]}")
        elif token.isalpha() and token.lower() in table:
            out.append(table[token.lower()])
        elif token.isascii() and token.isalpha():
            out.append(decode_word(token))
        else:
            out.append(token)
    return "".join(out)
