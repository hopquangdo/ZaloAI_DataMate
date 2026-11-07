"""Đo độ chính xác của luật unanswerable trên một tập có đáp án (không gọi LLM).

Chạy: uv run python scripts/check_unanswerable.py dataset/train/train
"""

from __future__ import annotations

import argparse
import json
from collections import Counter
from datetime import date
from pathlib import Path

from datamate.modules.data.ingestion import get_business
from datamate.modules.data.semantic.capabilities import capabilities
from datamate.modules.decision.verification import check_unanswerable


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("split_dir", type=Path)
    parser.add_argument("--show-wrong", type=int, default=12)
    args = parser.parse_args()
    answers = {
        json.loads(l)["id"]: json.loads(l)
        for l in (args.split_dir / "answers.jsonl").read_text(encoding="utf-8").splitlines()
        if l.strip()
    }
    caps_cache: dict = {}
    fired, correct, wrong = Counter(), Counter(), []
    truth = sum(1 for a in answers.values() if a["type"] == "unanswerable")
    caught = 0
    for line in (args.split_dir / "questions.jsonl").read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        q = json.loads(line)
        if q["business_id"] not in caps_cache:
            business = get_business(
                args.split_dir / "data" / q["business_id"], Path(".cache/businesses")
            )
            caps_cache[q["business_id"]] = capabilities(business)
        verdict = check_unanswerable(
            q["question"], date.fromisoformat(q["as_of_date"]), caps_cache[q["business_id"]]
        )
        if verdict is None:
            continue
        fired[verdict.rule] += 1
        if answers[q["id"]]["type"] == "unanswerable":
            correct[verdict.rule] += 1
            caught += 1
        else:
            wrong.append((verdict.rule, q["business_id"], q["question"], answers[q["id"]]["type"]))
    print(f"câu unanswerable thật: {truth}; luật bắt đúng: {caught} ({caught / max(truth, 1):.0%})")
    for rule, n in fired.most_common():
        print(f"  {rule:18s} bắn {n:4d}  đúng {correct[rule]:4d}  ({correct[rule] / n:.0%})")
    for rule, biz, text, kind in wrong[: args.show_wrong]:
        print(f"  SAI [{rule}] {biz} ({kind}) {text[:90]}")


if __name__ == "__main__":
    main()
