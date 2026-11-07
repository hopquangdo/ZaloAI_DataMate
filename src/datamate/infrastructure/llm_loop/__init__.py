"""Vòng lặp LLM dùng chung mọi tầng: sinh → chạy → soát → sửa theo feedback. Xem README.md."""

from datamate.infrastructure.llm_loop.engine import (
    AttemptError,
    Check,
    CheckKind,
    CheckResult,
    Engine,
)
from datamate.infrastructure.llm_loop.loop import LoopSettings, build_loop, initial_state
from datamate.infrastructure.llm_loop.state import LoopState, TraceStep

__all__ = [
    "AttemptError",
    "Check",
    "CheckKind",
    "CheckResult",
    "Engine",
    "LoopSettings",
    "LoopState",
    "TraceStep",
    "build_loop",
    "initial_state",
]
