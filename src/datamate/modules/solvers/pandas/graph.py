"""Bộ giải pandas = vòng lặp LLM chung (infrastructure.llm_loop) + PandasEngine + các Check.

generate → execute (sandbox) → rule check → [llm review] → finalize
"""

from __future__ import annotations

from collections.abc import Callable
from typing import Any

from datamate.infrastructure.llm import LLMClient
from datamate.infrastructure.llm_loop import Check, LoopSettings, build_loop
from datamate.modules.domain.answer import ABSTAIN
from datamate.modules.solvers.pandas.checks import LlmReviewCheck, RuleCheck
from datamate.modules.solvers.pandas.engine import PandasEngine
from datamate.modules.solvers.pandas.settings import AgentSettings


def build_graph(
    llm: LLMClient, namespace_factory: Callable[[], dict[str, Any]], settings: AgentSettings
) -> Any:
    """Dựng vòng lặp pandas; LLM review chỉ thêm khi bật trong settings."""
    checks: list[Check] = [RuleCheck()]
    if settings.llm_review:
        checks.append(LlmReviewCheck(llm))
    return build_loop(
        llm,
        PandasEngine(namespace_factory),
        checks=checks,
        settings=LoopSettings(max_attempts=settings.max_attempts, max_repeats=settings.max_repeats),
        fallback=ABSTAIN,
    )
