"""Đọc kết luận của LLM review (một dòng JSON {"ok": ..., "reason": ...})."""

from __future__ import annotations

import re
from dataclasses import dataclass

_OK = re.compile(r'"ok"\s*:\s*(true|false)', re.IGNORECASE)
_REASON = re.compile(r'"reason"\s*:\s*"(.*?)"', re.DOTALL)


@dataclass(frozen=True, slots=True)
class Verdict:
    """Kết luận của LLM review: đúng hay sai, và lý do."""

    ok: bool
    reason: str = ""


def parse_verdict(text: str) -> Verdict:
    """Không đọc được → coi là ok, để review hỏng không làm mất đáp án đúng."""
    match = _OK.search(text)
    if match is None or match.group(1).lower() == "true":
        return Verdict(ok=True)
    reason = _REASON.search(text)
    return Verdict(ok=False, reason=reason.group(1).strip() if reason else "đáp án chưa đúng")
