"""Cấu hình bỏ phiếu giữa các lần sinh (đọc từ biến môi trường, có giá trị mặc định)."""

from __future__ import annotations

import os
from dataclasses import dataclass

from datamate.infrastructure.config import load_dotenv


@dataclass(frozen=True)
class ConsensusSettings:
    """Số lần sinh và ngưỡng đồng thuận cho bỏ phiếu."""

    samples: int = 4  # số lần sinh tối đa (luân phiên pandas, sql…; 1 = tắt bỏ phiếu)
    min_agree: int = 2  # số lần sinh phải trùng đáp án mới trả lời, không thì abstain
    sample_temperature: float = 0.6  # nhiệt độ của các lần sinh thứ 2 trở đi

    @classmethod
    def from_env(cls) -> ConsensusSettings:
        load_dotenv()
        return cls(
            samples=int(os.environ.get("AGENT_SAMPLES", cls.samples)),
            min_agree=int(os.environ.get("AGENT_MIN_AGREE", cls.min_agree)),
            sample_temperature=float(
                os.environ.get("AGENT_SAMPLE_TEMPERATURE", cls.sample_temperature)
            ),
        )
