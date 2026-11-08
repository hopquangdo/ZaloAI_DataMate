"""Ví dụ mẫu tổng quát (few-shot) cho từng bộ giải.

Mỗi ví dụ là một file ``assets/examples/<tên>.md`` mô tả MỘT cấu trúc phép tính (đếm đơn, trung bình
mỗi đơn, tỉ lệ huỷ, xếp hạng...) trên bảng chuẩn tắc, không gắn với doanh nghiệp hay cách hỏi nào.
Không chọn ví dụ theo từ khoá: mọi câu đều nhận đủ bộ ví dụ (ngắn, giống hệt nhau giữa các câu nên
tận dụng được bộ đệm tiền tố của vLLM), để việc hiểu câu hỏi do LLM làm, không do regex làm.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from functools import cache
from pathlib import Path

EXAMPLE_DIR = Path(__file__).resolve().parents[3] / "assets" / "examples"
_CODE = re.compile(r"^```\w*\n(.*?)^```", re.DOTALL | re.MULTILINE)
_HEADER = (
    "# Ví dụ cấu trúc cách làm (CHỈ minh hoạ phép tính trên bảng chuẩn tắc: ngày, tên hàng, số "
    "trong ví dụ KHÔNG phải của câu hỏi này; dùng khoảng ngày ở phần Gợi ý, tên thật trong dữ liệu)"
)


@dataclass(frozen=True, slots=True)
class Example:
    """Một cấu trúc phép tính kèm lời giải cho từng bộ giải."""

    name: str
    description: str
    solutions: dict[str, str]  # bộ giải → khối code đã đóng khung


def parse_example(name: str, text: str) -> Example:
    """Đọc một file ví dụ: dòng ``mô tả:`` và các mục ``## <bộ giải>``."""
    description = ""
    solutions: dict[str, str] = {}
    sections = re.split(r"^## ", text, flags=re.MULTILINE)
    for line in sections[0].splitlines():
        if line.startswith("mô tả:"):
            description = line.removeprefix("mô tả:").strip()
    for section in sections[1:]:
        solver, _, body = section.partition("\n")
        match = _CODE.search(body)
        if match:
            solutions[solver.strip()] = match.group(0).strip()
    return Example(name, description, solutions)


@cache
def load_examples() -> tuple[Example, ...]:
    return tuple(
        parse_example(path.stem, path.read_text(encoding="utf-8"))
        for path in sorted(EXAMPLE_DIR.glob("*.md"))
    )


@cache
def render_examples(solver: str) -> str:
    """Khối ví dụ (đủ bộ) cho ``solver``; chuỗi rỗng nếu bộ giải không có ví dụ nào."""
    blocks = [
        f"Ví dụ — {example.description}\n{example.solutions[solver]}"
        for example in load_examples()
        if solver in example.solutions
    ]
    return f"{_HEADER}\n\n" + "\n\n".join(blocks) if blocks else ""
