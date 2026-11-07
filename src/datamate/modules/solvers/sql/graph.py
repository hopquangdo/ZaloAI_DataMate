"""Bộ giải SQL = vòng lặp LLM chung + SqlEngine (DuckDB chỉ đọc)."""

from __future__ import annotations

from collections.abc import Callable
from typing import Any

import pandas as pd

from datamate.infrastructure.llm import LLMClient
from datamate.infrastructure.llm_loop import LoopSettings, build_loop
from datamate.modules.domain.answer import ABSTAIN
from datamate.modules.solvers.sql.engine import SqlEngine


def build_sql_graph(
    llm: LLMClient,
    tables_factory: Callable[[], dict[str, pd.DataFrame]],
    settings: LoopSettings | None = None,
) -> Any:
    return build_loop(
        llm,
        SqlEngine(tables_factory),
        settings=settings or LoopSettings(repair_prompt="sql_repair"),
        fallback=ABSTAIN,
    )
