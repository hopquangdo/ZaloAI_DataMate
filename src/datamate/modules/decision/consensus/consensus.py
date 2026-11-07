"""Bỏ phiếu giữa nhiều lần sinh đáp án (self-consistency).

Điểm PA phạt −1 khi sai và 0 khi bỏ qua, nên chỉ trả lời khi đủ số lần sinh độc lập cho cùng
một đáp án; không đủ đồng thuận thì abstain.
"""

from __future__ import annotations

from collections import Counter
from collections.abc import Sequence

from datamate.core.text import normalize_text
from datamate.modules.domain.answer.schema import Answer, AnswerType, Table

Signature = tuple[object, ...]


def _cell(value: object) -> object:
    if isinstance(value, bool):
        return value
    if isinstance(value, (int, float)):
        return round(float(value), 2)
    return normalize_text(str(value))


def signature(answer: Answer) -> Signature | None:
    """Khoá chuẩn hoá để so hai đáp án; None nếu đáp án không phải một câu trả lời (abstain)."""
    if answer.type is AnswerType.ABSTAIN:
        return None
    if answer.type is AnswerType.UNANSWERABLE:
        return (answer.type,)
    value = answer.value
    if isinstance(value, Table):  # dòng là tập hợp; tên cột không dùng để so
        rows = sorted((tuple(_cell(c) for c in row) for row in value.rows), key=repr)
        return (answer.type, tuple(rows))
    if isinstance(value, tuple):  # list có thứ tự
        return (answer.type, tuple(_cell(v) for v in value))
    return (answer.type, _cell(value))


def vote(
    answers: Sequence[Answer],
    min_agree: int,
    sources: Sequence[str] | None = None,
    min_sources: int = 1,
) -> Answer | None:
    """Đáp án nhiều phiếu nhất nếu đạt `min_agree`; None nếu không đạt hoặc hoà ở mức cao nhất.

    ``sources[i]`` là bộ giải sinh ra ``answers[i]``. Đáp án thắng còn phải được ít nhất
    ``min_sources`` bộ giải khác nhau ủng hộ: hai lần sinh của cùng bộ giải hay mắc cùng lỗi.
    """
    groups: dict[Signature, list[Answer]] = {}
    supporters: dict[Signature, set[str]] = {}
    for index, answer in enumerate(answers):
        key = signature(answer)
        if key is not None:
            groups.setdefault(key, []).append(answer)
            source = sources[index] if sources is not None else str(index)
            supporters.setdefault(key, set()).add(source)
    if not groups:
        return None
    ranked = Counter({key: len(items) for key, items in groups.items()}).most_common()
    top_key, top = ranked[0]
    if top < min_agree or (len(ranked) > 1 and ranked[1][1] == top):
        return None
    if len(supporters[top_key]) < min_sources:
        return None
    return groups[top_key][0]
