"""Các Check của bộ giải pandas: luật rẻ trên code và đáp án, và (tuỳ chọn) LLM soát lại."""

from __future__ import annotations

from datamate.infrastructure.llm import LLMClient
from datamate.infrastructure.llm_loop import CheckResult, LoopState
from datamate.infrastructure.prompt_loader import render_prompt
from datamate.modules.solvers.pandas.review import (
    ReviewContext,
    answer_text,
    parse_verdict,
    review,
    review_feedback,
)


class RuleCheck:
    """Luật rẻ (không gọi LLM); mỗi luật chỉ bắn một lần cho mỗi câu."""

    name = "rule"
    kind = "rule"

    def __call__(self, state: LoopState) -> CheckResult | None:
        candidate = state["candidate"]
        context = ReviewContext(state.get("question", ""), state.get("code") or "", candidate)
        issues = review(context, skip=state.get("warned", []))
        if not issues:
            return None
        names = [issue.rule for issue in issues]
        return CheckResult(
            feedback=review_feedback(candidate, [issue.message for issue in issues]),
            names=names,
            trace={"issues": names},
        )


class LlmReviewCheck:
    """Nhờ LLM soát đáp án theo rulebook; bị bác đến cùng thì vòng lặp abstain."""

    name = "llm"
    kind = "llm"

    def __init__(self, llm: LLMClient) -> None:
        self._llm = llm

    def __call__(self, state: LoopState) -> CheckResult | None:
        candidate = state["candidate"]
        if not candidate.has_value:
            return None
        prompt = render_prompt(
            "review",
            question=state.get("question", ""),
            code=state.get("code") or "",
            answer=answer_text(candidate),
        )
        # giữ nguyên system prompt (toolkit + rulebook) để tận dụng cache
        completion = self._llm.complete([state["messages"][0], {"role": "user", "content": prompt}])
        verdict = parse_verdict(completion.text)
        tokens = completion.prompt_tokens + completion.completion_tokens
        if verdict.ok:
            return CheckResult(feedback=None, tokens=tokens, trace={"ok": True})
        return CheckResult(
            feedback=review_feedback(candidate, [verdict.reason]),
            tokens=tokens,
            trace={"ok": False, "reason": verdict.reason},
        )
