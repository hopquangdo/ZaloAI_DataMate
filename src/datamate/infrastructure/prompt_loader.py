"""Nạp prompt từ assets/prompts/*.md và điền biến `{name}`."""

from __future__ import annotations

import re
from functools import cache
from pathlib import Path

PROMPT_DIR = Path(__file__).resolve().parents[1] / "assets" / "prompts"
_PLACEHOLDER = re.compile(r"\{(\w+)\}")


@cache
def load_prompt(name: str) -> str:
    """Đọc nguyên văn `assets/prompts/<name>.md` (có cache)."""
    return (PROMPT_DIR / f"{name}.md").read_text(encoding="utf-8")


def render_prompt(name: str, **variables: str) -> str:
    """Thay `{biến}` bằng giá trị; dấu `{}` khác trong prompt được giữ nguyên.

    Chỉ quét template một lần nên giá trị được chèn (rulebook, README...) chứa `{...}` vẫn an toàn.
    Biến có trong template mà thiếu khi gọi -> KeyError.
    """

    def substitute(match: re.Match[str]) -> str:
        return str(variables[match.group(1)])

    return _PLACEHOLDER.sub(substitute, load_prompt(name))
