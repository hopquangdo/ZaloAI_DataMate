"""Cấu hình LLM từ biến môi trường (và file .env nếu có)."""

from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path


def load_dotenv(path: Path = Path(".env")) -> None:
    """Nạp KEY=VALUE từ .env, không ghi đè biến môi trường đã có."""
    if not path.exists():
        return
    for raw_line in path.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        os.environ.setdefault(key.strip(), value.strip().strip("\"'"))


@dataclass(frozen=True)
class LLMSettings:
    """Cấu hình kết nối LLM (API tương thích OpenAI)."""

    base_url: str
    api_key: str
    model: str
    temperature: float = 0.0
    max_tokens: int = 4096  # code ngắn; chừa chỗ cho prompt khi context chỉ 16k
    timeout_seconds: float = 180.0
    seed: int = 2026

    @classmethod
    def from_env(cls) -> LLMSettings:
        load_dotenv()
        model = os.environ.get("LLM_MODEL")
        if not model:
            raise RuntimeError("Thiếu biến môi trường LLM_MODEL (đặt trong .env hoặc môi trường)")
        return cls(
            base_url=os.environ.get("LLM_BASE_URL", "http://localhost:8000/v1"),
            api_key=os.environ.get("LLM_API_KEY", "EMPTY"),
            model=model,
            max_tokens=int(os.environ.get("LLM_MAX_TOKENS", cls.max_tokens)),
        )
