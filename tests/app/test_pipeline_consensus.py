import json
from datetime import date
from pathlib import Path

import pytest

from datamate.app.pipeline import Pipeline, Result
from datamate.app.question import Question
from datamate.infrastructure.llm import Completion
from datamate.modules.decision.consensus import ConsensusSettings

TRAIN = Path("dataset/train/train")
pytestmark = pytest.mark.skipif(not TRAIN.exists(), reason="chưa có dataset")

QUESTION = Question("q", "biz_101", "?", date(2026, 3, 4))


class ScriptedLLM:
    """LLM giả: mỗi lần gọi trả code gán đáp án kế tiếp trong kịch bản (chung giữa các bản sao)."""

    def __init__(self, values, state=None):
        self.values = values
        self.state = state if state is not None else {"calls": 0}

    def with_sampling(self, temperature, seed):
        return ScriptedLLM(self.values, self.state)

    def complete(self, messages):
        value = self.values[min(self.state["calls"], len(self.values) - 1)]
        self.state["calls"] += 1
        # trả cả khối python lẫn khối sql: mỗi bộ giải chỉ đọc khối của mình
        code = f'answer = {{"type": "number", "answer": {value}}}'
        sql = f"-- type: number\nSELECT {value}"
        text = f"```python\n{code}\n```\n```sql\n{sql}\n```"
        return Completion(text=text, prompt_tokens=1, completion_tokens=1)


def run(values, samples=3, min_agree=2) -> tuple[Result, int]:
    llm = ScriptedLLM(values)
    pipeline = Pipeline(
        TRAIN, None, llm, consensus=ConsensusSettings(samples=samples, min_agree=min_agree)
    )
    return pipeline.answer(QUESTION), llm.state["calls"]


def test_two_agreeing_samples_stop_early():
    result, calls = run([7, 7, 9])
    assert result.record == {"id": "q", "type": "number", "answer": 7}
    assert calls == 2 and len(result.log.samples) == 2


def test_cross_solver_agreement_after_four_samples():
    # thứ tự: pandas 1, sql 2, pandas 1, sql 1 → "1" được cả hai bộ giải ủng hộ
    result, calls = run([1, 2, 1, 1], samples=4)
    assert result.record["answer"] == 1 and calls == 4


def test_same_solver_agreement_alone_is_not_enough():
    # pandas ra 5 hai lần nhưng sql không đồng ý lần nào → abstain thay vì tin pandas
    result, calls = run([5, 9, 5, 8], samples=4)
    assert result.record == {"id": "q", "type": "abstain"} and calls == 4


def test_disagreement_abstains():
    result, calls = run([1, 2, 3, 4], samples=4)
    assert result.record == {"id": "q", "type": "abstain"} and calls == 4


def test_single_sample_mode_answers_directly():
    result, calls = run([4], samples=1, min_agree=1)
    assert result.record["answer"] == 4 and calls == 1


def test_submission_and_log_records_are_plain_json():
    result, _ = run([7, 7, 9])
    json.dumps(result.record)  # không dùng default=str: DTO lọt vào sẽ lỗi thay vì thành chuỗi
    json.dumps(result.log.to_record())


class NameLLM(ScriptedLLM):
    """Mọi lần sinh đều trả cùng một tên (qua cả hai bộ giải)."""

    def complete(self, messages):
        self.state["calls"] += 1
        name = self.values[0]
        code = f'answer = {{"type": "string", "answer": "{name}"}}'
        sql = f"-- type: string\nSELECT '{name}'"
        text = f"```python\n{code}\n```\n```sql\n{sql}\n```"
        return Completion(text=text, prompt_tokens=1, completion_tokens=1)


def test_unanswerable_rule_answers_without_calling_llm():
    llm = ScriptedLLM([1])
    pipeline = Pipeline(TRAIN, None, llm)
    question = Question("q", "biz_101", "Nhân viên nào tận tâm với khách nhất?", date(2026, 3, 4))
    result = pipeline.answer(question)
    assert result.record["type"] == "unanswerable"
    assert llm.state["calls"] == 0


def test_name_missing_from_data_is_not_answered():
    llm = NameLLM(["Sản phẩm không hề tồn tại XYZ"])
    result = Pipeline(TRAIN, None, llm).answer(QUESTION)
    assert result.record == {"id": "q", "type": "abstain"}
    assert any(step.get("review") == "sanity" for step in result.log.trace)
