"""Cấu hình của đồ thị agent (đọc từ biến môi trường, có giá trị mặc định)."""

from __future__ import annotations

import os
from dataclasses import dataclass

from datamate.infrastructure.config import load_dotenv


@dataclass(frozen=True)
class AgentSettings:
    """Số lượt sửa tối đa và có bật bước LLM review hay không."""

    max_attempts: int = 4  # 1 lần sinh + tối đa 3 lần sửa (lỗi chạy hoặc bị review trả lại)
    llm_review: bool = False  # bật bước LLM review; tắt cho tới khi đo được lợi ích
    max_repeats: int = 2  # cùng một lỗi liên tiếp bao nhiêu lượt thì bỏ lần sinh này (0 = tắt)

    @classmethod
    def from_env(cls) -> AgentSettings:
        load_dotenv()
        return cls(
            max_attempts=int(os.environ.get("AGENT_MAX_ATTEMPTS", cls.max_attempts)),
            llm_review=os.environ.get("AGENT_LLM_REVIEW", "").lower() in {"1", "true", "yes"},
            max_repeats=int(os.environ.get("AGENT_MAX_REPEATS", cls.max_repeats)),
        )
