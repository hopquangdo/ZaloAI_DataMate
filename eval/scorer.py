"""Chấm từng câu và tính PA (docs/TASK.md §6).

Đáp án chuẩn có dạng ``{"id", "type", "answer", "alias"}``. ``alias`` là:
- string: list các dạng chấp nhận thêm (vd. mã sản phẩm);
- list: list theo vị trí, mỗi phần tử là list alias của phần tử đó;
- table: list theo dòng, alias cho ô tên (cột đầu) của dòng đó.
"""

from __future__ import annotations

import math
from collections import Counter
from collections.abc import Callable, Iterable, Mapping, Sequence
from dataclasses import dataclass, field
from enum import Enum
from typing import Any

from datamate.core.text import normalize_text
from datamate.modules.domain.answer import AnswerType

_FLOAT_TOLERANCE = 1e-6

Json = Any


class Verdict(str, Enum):
    CORRECT = "correct"
    WRONG = "wrong"
    ABSTAIN = "abstain"

    @property
    def points(self) -> int:
        return {Verdict.CORRECT: 1, Verdict.ABSTAIN: 0, Verdict.WRONG: -1}[self]


# --- so khớp giá trị nguyên tố -------------------------------------------------


def _is_number(value: Json) -> bool:
    return isinstance(value, (int, float)) and not isinstance(value, bool) and math.isfinite(value)


def _number_matches(predicted: Json, reference: Json) -> bool:
    return _is_number(predicted) and abs(predicted - reference) <= _FLOAT_TOLERANCE


def _percent_matches(predicted: Json, reference: Json) -> bool:
    return _is_number(predicted) and abs(round(predicted, 2) - reference) <= _FLOAT_TOLERANCE


def _string_matches(predicted: Json, accepted: Iterable[str]) -> bool:
    if not isinstance(predicted, str):
        return False
    target = normalize_text(predicted)
    return any(target == normalize_text(form) for form in accepted)


def _cell_matches(predicted: Json, reference: Json, aliases: Sequence[str] = ()) -> bool:
    if isinstance(reference, str):
        return _string_matches(predicted, [reference, *aliases])
    return _number_matches(predicted, reference)


def _alias_at(aliases: Sequence[Json], index: int) -> list[str]:
    return list(aliases[index]) if index < len(aliases) and aliases[index] else []


# --- so khớp theo kiểu ----------------------------------------------------------


def _list_matches(predicted: Json, reference: list[Json], aliases: Sequence[Json]) -> bool:
    if not isinstance(predicted, list) or len(predicted) != len(reference):
        return False
    return all(
        _cell_matches(pred, ref, _alias_at(aliases, i))
        for i, (pred, ref) in enumerate(zip(predicted, reference, strict=True))
    )


def _column_order(predicted: list[Json], reference: list[str]) -> list[int] | None:
    """Vị trí cột dự đoán ứng với từng cột chuẩn: theo tên chuẩn hoá, không khớp thì theo vị trí."""
    if len(predicted) != len(reference) or not all(isinstance(c, str) for c in predicted):
        return None
    by_name = {normalize_text(name): i for i, name in enumerate(predicted)}
    order = [by_name.get(normalize_text(name)) for name in reference]
    if all(i is not None for i in order) and len(set(order)) == len(order):
        return [i for i in order if i is not None]
    return list(range(len(reference)))


def _row_matches(predicted: list[Json], reference: list[Json], aliases: list[str]) -> bool:
    return len(predicted) == len(reference) and all(
        _cell_matches(pred, ref, aliases if col == 0 else ())
        for col, (pred, ref) in enumerate(zip(predicted, reference, strict=True))
    )


def _table_matches(predicted: Json, reference: Mapping[str, Json], aliases: Sequence[Json]) -> bool:
    if not isinstance(predicted, Mapping):
        return False
    pred_columns, pred_rows = predicted.get("columns"), predicted.get("rows")
    if not isinstance(pred_columns, list) or not isinstance(pred_rows, list):
        return False
    order = _column_order(pred_columns, reference["columns"])
    ref_rows: list[list[Json]] = reference["rows"]
    if order is None or len(pred_rows) != len(ref_rows):
        return False
    if not all(isinstance(row, list) and len(row) == len(order) for row in pred_rows):
        return False

    # Dòng so như một tập hợp: mỗi dòng chuẩn ghép với đúng một dòng dự đoán.
    remaining = [[row[i] for i in order] for row in pred_rows]
    for index, ref_row in enumerate(ref_rows):
        row_aliases = _alias_at(aliases, index)
        match = next(
            (i for i, row in enumerate(remaining) if _row_matches(row, ref_row, row_aliases)),
            None,
        )
        if match is None:
            return False
        remaining.pop(match)
    return True


def _exact_matches(predicted: Json, reference: Json) -> bool:
    return type(predicted) is type(reference) and predicted == reference


Matcher = Callable[[Json, Json, list[Json]], bool]

_MATCHERS: Mapping[AnswerType, Matcher] = {
    AnswerType.NUMBER: lambda pred, ref, _: _number_matches(pred, ref),
    AnswerType.PERCENT: lambda pred, ref, _: _percent_matches(pred, ref),
    AnswerType.STRING: lambda pred, ref, aliases: _string_matches(pred, [ref, *aliases]),
    AnswerType.DATE: lambda pred, ref, _: _exact_matches(pred, ref),
    AnswerType.BOOLEAN: lambda pred, ref, _: _exact_matches(pred, ref),
    AnswerType.LIST: _list_matches,
    AnswerType.TABLE: _table_matches,
    AnswerType.UNANSWERABLE: lambda *_: True,
}


def _value_matches(answer_type: AnswerType, predicted: Json, reference: Json, alias: Json) -> bool:
    return _MATCHERS[answer_type](predicted, reference, list(alias or []))


def score_answer(prediction: Mapping[str, Json] | None, reference: Mapping[str, Json]) -> Verdict:
    """Chấm một câu: đúng kiểu và khớp giá trị thì đúng; abstain/thiếu thì 0; còn lại sai."""
    if prediction is None or prediction.get("type") in (None, AnswerType.ABSTAIN.value):
        return Verdict.ABSTAIN
    if prediction.get("type") != reference["type"]:
        return Verdict.WRONG
    matched = _value_matches(
        AnswerType(reference["type"]),
        prediction.get("answer"),
        reference.get("answer"),
        reference.get("alias"),
    )
    return Verdict.CORRECT if matched else Verdict.WRONG


# --- tổng hợp -------------------------------------------------------------------


@dataclass(frozen=True)
class Report:
    verdicts: Mapping[str, Verdict]
    reference_types: Mapping[str, str]
    by_type: Mapping[str, Counter[Verdict]] = field(init=False)

    def __post_init__(self) -> None:
        by_type: dict[str, Counter[Verdict]] = {}
        for qid, verdict in self.verdicts.items():
            by_type.setdefault(self.reference_types[qid], Counter())[verdict] += 1
        object.__setattr__(self, "by_type", by_type)

    @property
    def penalized_accuracy(self) -> float:
        if not self.verdicts:
            return 0.0
        return sum(v.points for v in self.verdicts.values()) / len(self.verdicts)

    def summary(self) -> str:
        total = Counter(self.verdicts.values())
        lines = [
            f"PA = {self.penalized_accuracy:.4f}  (N={len(self.verdicts)}, "
            f"đúng={total[Verdict.CORRECT]}, sai={total[Verdict.WRONG]}, "
            f"abstain={total[Verdict.ABSTAIN]})",
            "",
            f"{'type':<14}{'N':>6}{'đúng':>7}{'sai':>6}{'abstain':>9}{'PA':>9}",
        ]
        for answer_type, counts in sorted(self.by_type.items()):
            n = sum(counts.values())
            pa = (counts[Verdict.CORRECT] - counts[Verdict.WRONG]) / n
            lines.append(
                f"{answer_type:<14}{n:>6}{counts[Verdict.CORRECT]:>7}"
                f"{counts[Verdict.WRONG]:>6}{counts[Verdict.ABSTAIN]:>9}{pa:>9.4f}"
            )
        return "\n".join(lines)


def score_submission(
    predictions: Iterable[Mapping[str, Json]], references: Iterable[Mapping[str, Json]]
) -> Report:
    """Chấm toàn bộ; câu có trong đáp án mà thiếu trong bài nộp tính là abstain."""
    by_id = {p["id"]: p for p in predictions}
    reference_list = list(references)
    return Report(
        verdicts={r["id"]: score_answer(by_id.get(r["id"]), r) for r in reference_list},
        reference_types={r["id"]: r["type"] for r in reference_list},
    )
