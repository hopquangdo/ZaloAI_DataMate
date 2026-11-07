"""Client LLM OpenAI-compatible: dùng chung cho OpenRouter (thử nghiệm) và vLLM local (nộp bài)."""

from __future__ import annotations

import time
from dataclasses import dataclass, replace
from typing import Literal, TypedDict

from openai import APIConnectionError, APIStatusError, OpenAI, OpenAIError, RateLimitError

from datamate.infrastructure.config import LLMSettings

_RETRYABLE_STATUS = {408, 409, 429, 500, 502, 503, 504}
_MAX_RETRIES = 4

LLMError = OpenAIError  # mọi lỗi gọi API (kết nối, quá tải, 4xx/5xx)


class Message(TypedDict):
    """Một tin nhắn gửi cho LLM."""

    role: Literal["system", "user", "assistant"]
    content: str


@dataclass(frozen=True)
class Completion:
    """Kết quả một lần gọi LLM: văn bản và số token đã dùng."""

    text: str
    prompt_tokens: int
    completion_tokens: int


class LLMClient:
    """Client LLM tương thích OpenAI, tự thử lại khi gặp lỗi tạm thời."""

    def __init__(self, settings: LLMSettings) -> None:
        self._settings = settings
        self._client = OpenAI(
            base_url=settings.base_url, api_key=settings.api_key, timeout=settings.timeout_seconds
        )

    def with_sampling(self, temperature: float, seed: int) -> LLMClient:
        """Bản sao dùng nhiệt độ/seed khác — cho các lần sinh thêm của self-consistency."""
        return LLMClient(replace(self._settings, temperature=temperature, seed=seed))

    def complete(self, messages: list[Message]) -> Completion:
        for attempt in range(_MAX_RETRIES):
            try:
                response = self._client.chat.completions.create(
                    model=self._settings.model,
                    messages=list(messages),  # type: ignore[arg-type]
                    temperature=self._settings.temperature,
                    max_tokens=self._settings.max_tokens,
                    seed=self._settings.seed,
                )
                usage = response.usage
                return Completion(
                    text=response.choices[0].message.content or "",
                    prompt_tokens=usage.prompt_tokens if usage else 0,
                    completion_tokens=usage.completion_tokens if usage else 0,
                )
            except (APIConnectionError, RateLimitError, APIStatusError) as error:
                status = getattr(error, "status_code", None)
                retryable = status is None or status in _RETRYABLE_STATUS
                if not retryable or attempt == _MAX_RETRIES - 1:
                    raise
                time.sleep(2**attempt)
        raise RuntimeError("unreachable")
