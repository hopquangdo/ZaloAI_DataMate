"""Chạy kiểm tra hợp lý trên ĐÁP ÁN CHUẨN: luật tốt không được loại câu nào (không gọi LLM).

Chạy: uv run python scripts/check_sanity.py dataset/train/train
"""

from __future__ import annotations

import argparse
import json
from collections import Counter
from pathlib import Path

from datamate.modules.data.ingestion import get_business
from datamate.modules.decision.verification import check_answer, known_names
from datamate.modules.domain.answer import coerce_answer


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("split_dir", type=Path)
    args = parser.parse_args()
    read = lambda p: [
        json.loads(l) for l in p.read_text(encoding="utf-8").splitlines() if l.strip()
    ]  # noqa: E731
    answers = {a["id"]: a for a in read(args.split_dir / "answers.jsonl")}
    names_cache: dict[str, frozenset[str]] = {}
    rejected, checked = [], Counter()
    for q in read(args.split_dir / "questions.jsonl"):
        gold = answers[q["id"]]
        if gold["type"] in ("unanswerable", "abstain"):
            continue
        if q["business_id"] not in names_cache:
            business = get_business(
                args.split_dir / "data" / q["business_id"], Path(".cache/businesses")
            )
            names_cache[q["business_id"]] = known_names(business)
        answer = coerce_answer({"type": gold["type"], "answer": gold["answer"]})
        checked[gold["type"]] += 1
        reason = check_answer(answer, names_cache[q["business_id"]])
        if reason:
            rejected.append((q["business_id"], gold["type"], reason, q["question"]))
    print(f"đã kiểm {sum(checked.values())} đáp án chuẩn; bị loại nhầm: {len(rejected)}")
    for biz, kind, reason, text in rejected[:20]:
        print(f"  {biz} {kind}: {reason} | {text[:70]}")


if __name__ == "__main__":
    main()
