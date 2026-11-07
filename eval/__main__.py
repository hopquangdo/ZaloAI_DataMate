"""CLI: python -m eval <submission.jsonl> <answers.jsonl>."""

from __future__ import annotations

import argparse
from pathlib import Path

from datamate.infrastructure.jsonl import read_jsonl
from eval.scorer import score_submission


def main() -> None:
    parser = argparse.ArgumentParser(description="Chấm Penalized Accuracy.")
    parser.add_argument("submission", type=Path)
    parser.add_argument("answers", type=Path)
    parser.add_argument(
        "--only-answered",
        action="store_true",
        help="chỉ chấm các id có trong submission (khi chạy thử một phần tập câu hỏi)",
    )
    args = parser.parse_args()
    for path in (args.submission, args.answers):
        if not path.exists():
            parser.error(f"không thấy file {path}")
    predictions = list(read_jsonl(args.submission))
    references = list(read_jsonl(args.answers))
    if args.only_answered:
        done = {p["id"] for p in predictions}
        references = [r for r in references if r["id"] in done]
    report = score_submission(predictions, references)
    print(report.summary())


if __name__ == "__main__":
    main()
