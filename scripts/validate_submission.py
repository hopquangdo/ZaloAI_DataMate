"""Kiểm tra submission.jsonl trước khi nộp: đủ mọi id, không trùng, đúng kiểu và format đáp án.

Chạy:
    uv run python scripts/validate_submission.py reports/submission.jsonl dataset/public_test/public_test
    ... --fix reports/submission_final.jsonl   # ghi bản đã sửa: bỏ dòng trùng/lỗi, điền abstain cho id thiếu
"""

from __future__ import annotations

import argparse
import json
import sys
from collections import Counter
from pathlib import Path

from datamate.modules.domain.answer import FormatError, coerce_answer

_VALUE_TYPES = {"number", "percent", "string", "date", "boolean", "list", "table"}


def _read(path: Path) -> list[dict]:
    return [json.loads(x) for x in path.read_text(encoding="utf-8").splitlines() if x.strip()]


def _problem(record: dict) -> str | None:
    kind = record.get("type")
    if kind in ("unanswerable", "abstain"):
        return None
    if kind not in _VALUE_TYPES:
        return f"kiểu không hợp lệ: {kind!r}"
    try:
        coerce_answer({"type": kind, "answer": record.get("answer")})
    except FormatError as error:
        return f"sai format: {error}"
    return None


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("submission", type=Path)
    parser.add_argument("split_dir", type=Path, help="thư mục có questions.jsonl")
    parser.add_argument("--fix", type=Path, help="ghi bản đã sửa ra file này")
    args = parser.parse_args()

    wanted = [q["id"] for q in _read(args.split_dir / "questions.jsonl")]
    records = _read(args.submission)
    counts = Counter(r.get("id") for r in records)
    duplicates = [i for i, n in counts.items() if n > 1]
    unknown = [i for i in counts if i not in set(wanted)]
    missing = [i for i in wanted if i not in counts]
    broken = {r["id"]: p for r in records if (p := _problem(r))}

    types = Counter(r.get("type") for r in records)
    print(f"{len(records)} dòng / {len(wanted)} câu; kiểu: {dict(types)}")
    print(
        f"thiếu {len(missing)}, trùng {len(duplicates)}, id lạ {len(unknown)}, lỗi format {len(broken)}"
    )
    for qid, problem in list(broken.items())[:10]:
        print(f"  {qid}: {problem}")

    if args.fix:
        kept: dict[str, dict] = {}
        for record in records:  # dòng sau cùng của một id thắng (chạy lại đè lên)
            if record.get("id") in set(wanted):
                kept[record["id"]] = (
                    record
                    if record["id"] not in broken
                    else {"id": record["id"], "type": "abstain"}
                )
        fixed = [kept.get(i, {"id": i, "type": "abstain"}) for i in wanted]
        args.fix.write_text(
            "".join(json.dumps(r, ensure_ascii=False) + "\n" for r in fixed), encoding="utf-8"
        )
        print(f"đã ghi {len(fixed)} dòng vào {args.fix}")
    ok = not (missing or duplicates or unknown or broken)
    print("HỢP LỆ" if ok else "CHƯA HỢP LỆ")
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
