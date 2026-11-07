"""Phân tích một lượt chạy để biết mất điểm ở đâu.

Đọc run_log.jsonl (mỗi câu: câu hỏi, đáp án, các lần sinh, trace từng lượt có solver / code / lỗi)
và answers.jsonl, rồi in:
- PA theo nguồn đáp án (luật code / pandas / sql), theo nhóm câu hỏi, theo kiểu đáp án, theo
  doanh nghiệp;
- thống kê lỗi theo bộ giải (KeyError, BinderException…) và số lần luật / kiểm tra bắn;
- thời gian, token trung bình.
Với ``--cases`` ghi các câu sai / abstain ra JSONL (câu hỏi, đáp án chuẩn, các lần sinh, lỗi cuối
của từng bộ giải) để đọc từng ca.

Chạy:
    uv run python -m eval.breakdown reports/run_log.jsonl dataset/train/train/answers.jsonl \\
        --cases reports/cases.jsonl
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from collections import Counter, defaultdict
from pathlib import Path

from datamate.core.text import fold
from eval.scorer import Verdict, score_answer

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
from analyze_questions import TOPICS, first_match


def _read(path: Path) -> list[dict]:
    return [json.loads(x) for x in path.read_text(encoding="utf-8").splitlines() if x.strip()]


def _source(entry: dict) -> str:
    """Đáp án đến từ đâu: luật unanswerable, hay bộ giải của lần sinh cho ra đáp án đó."""
    trace = entry.get("trace", [])
    for step in trace:
        if str(step.get("review", "")).startswith("rule:"):
            return step["review"]
    final = entry.get("answer", {})
    if final.get("type") == "abstain":
        return "abstain"
    solvers = {str(s["solver"]) for s in trace if s.get("answer") == final and s.get("solver")}
    return "+".join(sorted(solvers)) or "?"


def _error_kind(message: str) -> str:
    """Loại lỗi gọn: tên exception gốc (KeyError, BinderException…) hoặc câu đầu của feedback."""
    names = re.findall(r"\b([A-Z]\w*(?:Error|Exception|Rejected|Failed))\b", message)
    if names:
        return names[-1]
    return message.split(":", 1)[0][:40]


def _row(name: str, verdicts: list[Verdict]) -> str:
    n = len(verdicts)
    correct = sum(v is Verdict.CORRECT for v in verdicts)
    wrong = sum(v is Verdict.WRONG for v in verdicts)
    pa = (correct - wrong) / n if n else 0.0
    return f"{name[:30]:30s} {n:5d} {correct:6d} {wrong:5d} {n - correct - wrong:8d} {pa:8.4f}"


def _table(title: str, groups: dict[str, list[Verdict]]) -> None:
    print(f"\n== {title}")
    print(f"{'':30s} {'N':>5s} {'đúng':>6s} {'sai':>5s} {'abstain':>8s} {'PA':>8s}")
    for name, verdicts in sorted(groups.items(), key=lambda kv: -len(kv[1])):
        print(_row(name, verdicts))


def _case(entry: dict, reference: dict, verdict: Verdict) -> dict:
    last_errors: dict[str, str] = {}
    for step in entry.get("trace", []):
        if step.get("error"):
            last_errors[str(step.get("solver", "?"))] = str(step["error"])[:300]
    return {
        "id": entry["id"],
        "business_id": entry.get("business_id"),
        "question": entry.get("question"),
        "verdict": verdict.value,
        "reference": {"type": reference["type"], "answer": reference.get("answer")},
        "answer": entry.get("answer"),
        "samples": entry.get("samples"),
        "last_errors": last_errors,
        "seconds": entry.get("seconds"),
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("run_log", type=Path)
    parser.add_argument("answers", type=Path)
    parser.add_argument("--cases", type=Path, help="ghi các câu sai / abstain ra file JSONL này")
    args = parser.parse_args()

    answers = {a["id"]: a for a in _read(args.answers)}
    groups: dict[str, dict[str, list[Verdict]]] = defaultdict(lambda: defaultdict(list))
    errors: dict[str, Counter[str]] = defaultdict(Counter)
    checks: Counter[str] = Counter()
    seconds, tokens, cases = [], [], []
    for entry in _read(args.run_log):
        reference = answers.get(entry["id"])
        if reference is None:
            continue
        verdict = score_answer(entry.get("answer"), reference)
        topic = first_match(fold(entry.get("question") or ""), TOPICS, "khac")
        groups["theo nguồn đáp án"][_source(entry)].append(verdict)
        groups["theo nhóm câu hỏi"][topic].append(verdict)
        groups["theo kiểu đáp án chuẩn"][reference["type"]].append(verdict)
        groups["theo doanh nghiệp"][entry.get("business_id", "?")].append(verdict)
        for step in entry.get("trace", []):
            if step.get("error"):
                errors[str(step.get("solver", "?"))][_error_kind(str(step["error"]))] += 1
            review = str(step.get("review", ""))
            if review:
                checks[review] += 1
        seconds.append(entry.get("seconds") or 0.0)
        tokens.append(entry.get("tokens") or 0)
        if verdict is not Verdict.CORRECT:
            cases.append(_case(entry, reference, verdict))

    total = [v for vs in groups["theo kiểu đáp án chuẩn"].values() for v in vs]
    print(_row("TỔNG", total))
    for title, group in groups.items():
        _table(title, group)
    print("\n== lỗi theo bộ giải (mọi lượt, kể cả lượt đã sửa được)")
    for solver, counter in errors.items():
        print(f"  {solver}: " + ", ".join(f"{k}×{n}" for k, n in counter.most_common(12)))
    print("\n== luật / kiểm tra đã bắn: " + ", ".join(f"{k}×{n}" for k, n in checks.most_common()))
    if seconds:
        print(f"\ntrung bình {sum(seconds) / len(seconds):.1f}s/câu, "
              f"{sum(tokens) / len(tokens):.0f} token/câu")
    if args.cases:
        args.cases.write_text(
            "".join(json.dumps(c, ensure_ascii=False) + "\n" for c in cases), encoding="utf-8"
        )
        print(f"đã ghi {len(cases)} câu sai / abstain vào {args.cases}")


if __name__ == "__main__":
    main()
