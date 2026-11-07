"""Pipeline cho một câu hỏi: nạp dữ liệu → hiểu câu hỏi → agent (bỏ phiếu) → đáp án."""

from __future__ import annotations

import time
from dataclasses import dataclass
from functools import partial
from pathlib import Path
from typing import Any

from datamate.app.business_registry import BusinessRegistry, PreparedBusiness
from datamate.app.knowledge import load_knowledge
from datamate.app.question import Question
from datamate.app.run_log import Outcome, RunLog
from datamate.infrastructure.llm import LLMClient, LLMError, Message
from datamate.infrastructure.llm_loop import LoopSettings, LoopState, initial_state
from datamate.infrastructure.prompt_loader import load_prompt, render_prompt
from datamate.modules.data.ingestion import Business
from datamate.modules.decision.consensus import ConsensusSettings, vote
from datamate.modules.decision.verification import check_answer, check_unanswerable
from datamate.modules.domain.answer import ABSTAIN, Answer
from datamate.modules.solvers.pandas import AgentSettings, build_graph, build_namespace
from datamate.modules.solvers.sql import FUNCTIONS_DOC, build_sql_graph
from datamate.modules.understanding.normalize import understand

# Thứ tự các lần sinh: luân phiên hai bộ giải độc lập để hai đáp án trùng nhau đáng tin hơn.
SOLVER_ORDER = ("pandas", "sql")


@dataclass(frozen=True, slots=True)
class Result:
    """Kết quả của một câu hỏi: đáp án chốt và log để gỡ lỗi."""

    answer: Answer
    log: RunLog

    @property
    def record(self) -> dict[str, object]:
        """Dòng của submission.jsonl."""
        return self.answer.to_record(self.log.question.id)


class Pipeline:
    """Trả lời từng câu hỏi của một tập (dùng chung rulebook, lịch âm, dữ liệu doanh nghiệp)."""

    def __init__(
        self,
        split_dir: Path,
        cache_dir: Path | None,
        llm: LLMClient,
        agent: AgentSettings | None = None,
        consensus: ConsensusSettings | None = None,
    ) -> None:
        self._agent = agent or AgentSettings()
        self._consensus = consensus or ConsensusSettings()
        # Lần sinh đầu dùng cấu hình gốc (nhiệt độ thấp); các lần sau cần ngẫu nhiên để đa dạng.
        self._llms = [llm] + [
            llm.with_sampling(self._consensus.sample_temperature, seed=1000 + i)
            for i in range(1, self._consensus.samples)
        ]
        self._knowledge = load_knowledge(split_dir)
        self._systems = {
            "pandas": render_prompt(
                "system", toolkit=load_prompt("toolkit"), rulebook=self._knowledge.rulebook
            ),
            "sql": render_prompt(
                "sql_system", functions=FUNCTIONS_DOC, rulebook=self._knowledge.rulebook
            ),
        }
        self._businesses = BusinessRegistry(split_dir / "data", cache_dir)

    def answer(self, question: Question) -> Result:
        """Trả lời một câu hỏi.

        Lỗi gọi API làm lần sinh đó bị bỏ qua; lỗi khác (bug, dữ liệu hỏng) được ném lên để
        nơi gọi quyết định, không bị nuốt thành abstain im lặng.
        """
        started = time.perf_counter()
        prepared = self._businesses.get(question.business_id)
        verdict = check_unanswerable(question.text, question.as_of_date, prepared.capabilities)
        if verdict is not None:  # luật code đã chắc: không tốn lượt gọi LLM
            answer = Answer.unanswerable(verdict.reason)
            step = {"review": f"rule:{verdict.rule}", "reason": verdict.reason}
            rule_state: LoopState = {"trace": [step]}  # type: ignore[list-item]
            outcome = Outcome(answer, (answer,), (rule_state,), None)
            log = RunLog.from_outcome(question, answer, outcome, time.perf_counter() - started)
            return Result(answer, log)
        user = self._user_message(prepared, question)
        outcome = self._sample_until_consensus(prepared, question, user)
        answer = outcome.winner or ABSTAIN
        log = RunLog.from_outcome(question, answer, outcome, time.perf_counter() - started)
        return Result(answer, log)

    def _attempts(self) -> list[tuple[str, LLMClient]]:
        """(bộ giải, llm) cho từng lần sinh: lượt đầu của mỗi bộ giải dùng nhiệt độ gốc."""
        plan = []
        for index in range(self._consensus.samples):
            solver = SOLVER_ORDER[index % len(SOLVER_ORDER)]
            llm = self._llms[0] if index < len(SOLVER_ORDER) else self._llms[index - 1]
            plan.append((solver, llm))
        return plan

    def _min_solvers(self) -> int:
        """Có từ 2 bộ giải và đòi từ 2 phiếu: hai phiếu phải đến từ hai bộ giải khác nhau."""
        used = {solver for solver, _ in self._attempts()}
        return 2 if len(used) >= 2 and self._consensus.min_agree >= 2 else 1

    def _graph(self, solver: str, llm: LLMClient, business: Business, question: Question) -> Any:
        if solver == "sql":
            settings = LoopSettings(
                max_attempts=self._agent.max_attempts,
                max_repeats=self._agent.max_repeats,
                repair_prompt="sql_repair",
            )
            return build_sql_graph(llm, lambda: business.tables, settings)
        namespace = partial(build_namespace, business, question.as_of_date, self._knowledge.lunar)
        return build_graph(llm, namespace, self._agent)

    def _sample_until_consensus(
        self, prepared: PreparedBusiness, question: Question, user: str
    ) -> Outcome:
        samples: list[Answer] = []
        sources: list[str] = []
        states: list[LoopState] = []
        error: str | None = None
        winner: Answer | None = None
        for solver, llm in self._attempts():
            graph = self._graph(solver, llm, prepared.business, question)
            messages: list[Message] = [
                {"role": "system", "content": self._systems[solver]},
                {"role": "user", "content": user},
            ]
            try:
                state: LoopState = graph.invoke(initial_state(question.text, messages))
            except LLMError as exc:  # API hỏng hoặc quá tải: bỏ lần sinh này
                error = f"{type(exc).__name__}: {exc}"
                state = {}
            answer = state.get("answer") or ABSTAIN
            problem = check_answer(answer, prepared.names)
            trace = [{**step, "solver": solver} for step in state.get("trace", [])]
            if problem is not None:  # đáp án sai rõ ràng: không cho tính phiếu
                trace.append({"review": "sanity", "reason": problem, "solver": solver})
                answer = ABSTAIN
            states.append({**state, "trace": trace})  # type: ignore[typeddict-item]
            samples.append(answer)
            sources.append(solver)
            winner = vote(samples, self._consensus.min_agree, sources, self._min_solvers())
            if winner is not None:  # đã đủ đồng thuận: dừng sớm cho đỡ tốn
                break
        return Outcome(winner, tuple(samples), tuple(states), error)

    def _user_message(self, prepared: PreparedBusiness, question: Question) -> str:
        understanding = understand(question.text, question.as_of_date, prepared.entities)
        return render_prompt(
            "user",
            business_id=prepared.business.business_id,
            readme=prepared.business.readme.strip(),
            tables=prepared.profile,
            question=question.text,
            as_of_date=question.as_of_date.isoformat(),
            hints=understanding.render(question.text),
        )
