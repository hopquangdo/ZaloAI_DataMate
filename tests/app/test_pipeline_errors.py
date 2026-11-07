from datetime import date
from pathlib import Path

import httpx
import openai
import pytest

from datamate.app.pipeline import Pipeline
from datamate.app.question import Question
from datamate.modules.decision.consensus import ConsensusSettings

TRAIN = Path("dataset/train/train")
pytestmark = pytest.mark.skipif(not TRAIN.exists(), reason="chưa có dataset")

QUESTION = Question("q", "biz_101", "?", date(2026, 3, 4))


class _FailingLLM:
    def __init__(self, error: Exception) -> None:
        self._error = error

    def with_sampling(self, temperature: float, seed: int) -> "_FailingLLM":
        return self

    def complete(self, messages):
        raise self._error


def _pipeline(error: Exception) -> Pipeline:
    return Pipeline(
        TRAIN,
        None,
        _FailingLLM(error),  # type: ignore[arg-type]
        consensus=ConsensusSettings(samples=1, min_agree=1),
    )


def test_api_failure_degrades_to_abstain_and_is_logged() -> None:
    request = httpx.Request("POST", "http://localhost/v1/chat/completions")
    result = _pipeline(openai.APIConnectionError(request=request)).answer(QUESTION)
    assert result.record == {"id": "q", "type": "abstain"}
    assert result.log.error_kind == "api"
    assert "APIConnectionError" in (result.log.error or "")


def test_programming_error_is_not_swallowed() -> None:
    with pytest.raises(RuntimeError, match="bug thật"):
        _pipeline(RuntimeError("bug thật")).answer(QUESTION)
