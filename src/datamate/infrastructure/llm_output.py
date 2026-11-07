"""Đọc kết quả LLM trả về dạng văn bản."""

from __future__ import annotations

import re

_CODE_BLOCK = re.compile(r"```(?:python|py)?\s*\n(.*?)```", re.DOTALL)


def extract_code(text: str) -> str | None:
    """Khối ```python``` cuối cùng trong câu trả lời của LLM."""
    blocks = _CODE_BLOCK.findall(text)
    if blocks:
        return str(blocks[-1]).strip()
    if "```" in text:  # khối chưa đóng (hết token giữa chừng) → lấy phần sau rào mở
        tail = text.split("```", 1)[1]
        return tail.removeprefix("python").removeprefix("py").strip() or None
    return text.strip() if re.search(r"^\s*answer\s*=", text, re.MULTILINE) else None
