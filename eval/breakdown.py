"""Phân tích một lượt chạy: PA theo doanh nghiệp, theo nguồn đáp án (luật code / pandas / sql),
và thời gian, token trung bình. Đọc run_log.jsonl (có business_id, trace) và answers.jsonl.

Chạy: uv run python -m eval.breakdown reports/run_log.jsonl dataset/train/train/answers.jsonl
"""

from __future__ import annotations

import argparse
import json
from collections import defaultdict
from pathlib import Path

from eval.scorer import Verdict, score_answer


def _read(path: Path) -> list[dict]:
    return [json.loads(x) for x in path.read_text(encoding="utf-8").splitlines() if x.strip()]


def _source(entry: dict) -> str:
    """Đáp án đến từ đâu: luật unanswerable, hay bộ giải của lần sinh đầu tiên cho đáp án đó."""
    trace = entry.get("trace", [])
    for step in trace:
        if str(step.get("review", "")).startswith("rule:"):
            return step["review"]
    final = entry.get("answer", {})
    for step in trace:
        if step.get("answer") == final and step.get("solver"):
            return str(step["solver"])
    return "abstain" if final.get("type") == "abstain" else "?"


def _row(name: str, verdicts: list[Verdict]) -> str:
    n = len(verdicts)
    correct = sum(v is Verdict.CORRECT for v in verdicts)
    wrong = sum(v is Verdict.WRONG for v in verdicts)
    pa = (correct - wrong) / n if n else 0.0
    return f"{name:24s} {n:5d} {correct:6d} {wrong:5d} {n - correct - wrong:8d} {pa:8.4f}"


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("run_log", type=Path)
    parser.add_argument("answers", type=Path)
    args = parser.parse_args()
    answers = {a["id"]: a for a in _read(args.answers)}
    by_business, by_source = defaultdict(list), defaultdict(list)
    seconds, tokens = [], []
    for entry in _read(args.run_log):
        reference = answers.get(entry["id"])
        if reference is None:
            continue
        verdict = score_answer(entry.get("answer"), reference)
        by_business[entry.get("business_id", "?")].append(verdict)
        by_source[_source(entry)].append(verdict)
        seconds.append(entry.get("seconds", 0.0))
        tokens.append(entry.get("tokens", 0))
    header = f"{'':24s} {'N':>5s} {'đúng':>6s} {'sai':>5s} {'abstain':>8s} {'PA':>8s}"
    for title, groups in (("theo nguồn đáp án", by_source), ("theo doanh nghiệp", by_business)):
        print(f"\n== {title}\n{header}")
        for name, verdicts in sorted(groups.items(), key=lambda kv: -len(kv[1])):
            print(_row(name, verdicts))
    if seconds:
        print(
            f"\ntrung bình {sum(seconds) / len(seconds):.1f}s/câu, {sum(tokens) / len(tokens):.0f} token/câu"
        )


if __name__ == "__main__":
    main()
