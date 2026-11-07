from types import SimpleNamespace
from typing import Any

import httpx
import openai
import pytest

from datamate.infrastructure import llm as llm_module
from datamate.infrastructure.config import LLMSettings
from datamate.infrastructure.llm import LLMClient

REQUEST = httpx.Request("POST", "http://localhost/v1/chat/completions")
MESSAGES: list[Any] = [{"role": "user", "content": "xin chào"}]


def _response(text: str = "ok") -> SimpleNamespace:
    return SimpleNamespace(
        choices=[SimpleNamespace(message=SimpleNamespace(content=text))],
        usage=SimpleNamespace(prompt_tokens=3, completion_tokens=2),
    )


class _Create:
    """Giả `chat.completions.create`: lần lượt ném lỗi / trả kết quả đã định."""

    def __init__(self, *outcomes: Any) -> None:
        self.outcomes = list(outcomes)
        self.calls = 0

    def __call__(self, **kwargs: Any) -> Any:
        outcome = self.outcomes[min(self.calls, len(self.outcomes) - 1)]
        self.calls += 1
        if isinstance(outcome, Exception):
            raise outcome
        return outcome


def _client(create: _Create) -> LLMClient:
    client = LLMClient(LLMSettings("http://localhost:1/v1", "key", "model"))
    client._client = SimpleNamespace(
        chat=SimpleNamespace(completions=SimpleNamespace(create=create))
    )  # type: ignore[assignment]
    return client


@pytest.fixture(autouse=True)
def _no_sleep(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(llm_module.time, "sleep", lambda seconds: None)


def test_returns_text_and_token_usage() -> None:
    completion = _client(_Create(_response("xin chào"))).complete(MESSAGES)
    assert (completion.text, completion.prompt_tokens, completion.completion_tokens) == (
        "xin chào",
        3,
        2,
    )


def test_retries_transient_errors_then_succeeds() -> None:
    create = _Create(
        openai.APIConnectionError(request=REQUEST),
        openai.APIConnectionError(request=REQUEST),
        _response(),
    )
    assert _client(create).complete(MESSAGES).text == "ok"
    assert create.calls == 3


def test_does_not_retry_client_errors() -> None:
    bad_request = openai.BadRequestError(
        "bad", response=httpx.Response(400, request=REQUEST), body=None
    )
    create = _Create(bad_request)
    with pytest.raises(openai.BadRequestError):
        _client(create).complete(MESSAGES)
    assert create.calls == 1


def test_gives_up_after_max_retries() -> None:
    create = _Create(openai.APIConnectionError(request=REQUEST))
    with pytest.raises(openai.APIConnectionError):
        _client(create).complete(MESSAGES)
    assert create.calls == llm_module._MAX_RETRIES


def test_with_sampling_changes_only_temperature_and_seed() -> None:
    base = LLMClient(LLMSettings("http://localhost:1/v1", "key", "model"))
    other = base.with_sampling(0.7, seed=5)
    assert (other._settings.temperature, other._settings.seed) == (0.7, 5)
    assert other._settings.model == "model"
    assert base._settings.temperature == 0.0
