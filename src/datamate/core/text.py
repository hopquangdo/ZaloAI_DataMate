"""Tiện ích chữ dùng chung: chuẩn hoá theo luật chấm, bỏ dấu, cắt ngắn."""

from __future__ import annotations

import re
import unicodedata

_WHITESPACE = re.compile(r"\s+")


def normalize_text(value: str) -> str:
    """NFC → chữ thường → bỏ ký tự không phải chữ/số → gộp khoảng trắng. Không bỏ dấu.

    Theo luật chấm của đề (TASK.md §6.1).
    """
    text = unicodedata.normalize("NFC", value).lower()
    text = "".join(char if _is_kept(char) else " " for char in text)
    return _WHITESPACE.sub(" ", text).strip()


def fold(text: str) -> str:
    """Chữ thường, bỏ dấu, đ→d — để so khớp tên cột/câu hỏi viết không dấu."""
    decomposed = unicodedata.normalize("NFD", text.lower().replace("đ", "d"))
    return "".join(c for c in decomposed if unicodedata.category(c) != "Mn")


def shorten(text: str, limit: int) -> str:
    """Cắt chuỗi dài để không làm phình prompt (context chỉ 16k)."""
    return text if len(text) <= limit else text[: limit - 1] + "…"


def _is_kept(char: str) -> bool:
    """Giữ chữ, số (kể cả dấu kết hợp) và khoảng trắng; ký tự khác thành dấu cách."""
    return char.isspace() or unicodedata.category(char)[0] in {"L", "N", "M"}
