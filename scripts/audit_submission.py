"""Audit nghiêm ngặt submission.jsonl theo rulebook §9 và đối chiếu câu đơn giản với bảng chuẩn tắc.

    uv run python scripts/audit_submission.py reports/submission_final.jsonl dataset/public_test/public_test
"""

from __future__ import annotations

import json
import math
import re
import sys
from collections import Counter, defaultdict
from datetime import date
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import check_canonical as cc  # noqa: E402

from datamate.core.text import fold  # noqa: E402
from datamate.modules.data.canonical import build_canonical  # noqa: E402
from datamate.modules.data.ingestion import load_business  # noqa: E402
from datamate.modules.understanding.normalize import normalize_question, time_hints  # noqa: E402

DATE_FULL = re.compile(r"^\d{4}-\d{2}-\d{2}$")
DATE_MONTH = re.compile(r"^\d{4}-\d{2}$")


def format_problems(row: dict) -> list[str]:
    kind, answer = row.get("type"), row.get("answer")
    if kind in ("abstain", "unanswerable"):
        if "answer" in row:
            return ["abstain/unanswerable có trường answer"]
        reason = row.get("reason")
        return ["reason không phải chuỗi"] if reason is not None and not isinstance(reason, str) else []
    out: list[str] = []
    is_num = isinstance(answer, (int, float)) and not isinstance(answer, bool)
    if kind == "number":
        if not is_num:
            out.append("number không phải số")
        elif isinstance(answer, float) and not math.isfinite(answer):
            out.append("number không hữu hạn")
        elif isinstance(answer, float) and answer.is_integer():
            out.append("number là float nguyên (nên là int)")
    elif kind == "percent":
        if not is_num:
            out.append("percent không phải số")
        elif isinstance(answer, float) and round(answer, 2) != answer:
            out.append("percent quá 2 chữ số thập phân")
    elif kind == "date":
        if not (isinstance(answer, str) and (DATE_FULL.match(answer) or DATE_MONTH.match(answer))):
            out.append(f"date sai định dạng: {answer!r}")
    elif kind == "boolean":
        if not isinstance(answer, bool):
            out.append("boolean không phải true/false")
    elif kind == "string":
        if not isinstance(answer, str):
            out.append("string không phải chuỗi")
    elif kind == "list":
        if not isinstance(answer, list):
            out.append("list không phải mảng")
    elif kind == "table":
        ok = isinstance(answer, dict) and isinstance(answer.get("columns"), list) and isinstance(
            answer.get("rows"), list
        )
        if not ok:
            out.append("table sai cấu trúc")
    else:
        out.append(f"type lạ: {kind!r}")
    return out


def main() -> None:
    sub_path, split = Path(sys.argv[1]), Path(sys.argv[2])
    rows = [json.loads(x) for x in sub_path.read_text(encoding="utf-8").splitlines() if x.strip()]
    questions = {q["id"]: q for q in (json.loads(x) for x in (split / "questions.jsonl").read_text(encoding="utf-8").splitlines() if x.strip())}
    print("== Định dạng ==")
    problems = Counter()
    for r in rows:
        for p in format_problems(r):
            problems[p] += 1
    print("  dòng:", len(rows), "| lỗi định dạng:", dict(problems) or "không có")
    print("  kiểu:", dict(Counter(r["type"] for r in rows)))

    by_biz = defaultdict(list)
    for r in rows:
        by_biz[questions[r["id"]]["business_id"]].append(r)
    print("\n== Theo doanh nghiệp: trả lời / số 0 / unanswerable ==")
    for biz, rs in sorted(by_biz.items()):
        ans = [r for r in rs if r["type"] not in ("abstain", "unanswerable")]
        zeros = sum(1 for r in ans if r["type"] in ("number", "percent") and r.get("answer") == 0)
        print(f"  {biz}: {len(rs):3d} câu | trả lời {len(ans):3d} | bằng 0: {zeros:2d} | unanswerable {sum(1 for r in rs if r['type'] == 'unanswerable'):2d}")

    print("\n== Đối chiếu câu đơn giản với bảng chuẩn tắc (doanh thu, số đơn, đơn huỷ, tỉ lệ huỷ) ==")
    stats = defaultdict(Counter)
    shown = defaultdict(list)
    for biz, rs in sorted(by_biz.items()):
        canon = build_canonical(load_business(split / "data" / biz).tables).tables
        for r in rs:
            if r["type"] not in ("number", "percent"):
                continue
            q = questions[r["id"]]
            kind = cc._kind(fold(q["question"]))
            if kind is None:
                continue
            hints = time_hints(normalize_question(q["question"]), date.fromisoformat(q["as_of_date"]))
            if len(hints) != 1:
                continue
            try:
                pred = cc._predict(kind, canon, hints[0].period.start, hints[0].period.end)
            except (KeyError, ValueError):
                pred = None
            if pred is None:
                continue
            tolerance = 0.006 if kind == "cancel_rate" else 0.5
            same = abs(pred - float(r["answer"])) <= tolerance
            stats[biz]["khớp" if same else "lệch"] += 1
            if not same and len(shown[biz]) < 2:
                shown[biz].append(f"{q['question'][:60]} | bảng chuẩn={pred:g} | nộp={r['answer']}")
    for biz, c in sorted(stats.items()):
        print(f"  {biz}: khớp {c['khớp']}/{c['khớp'] + c['lệch']}")
        for line in shown[biz]:
            print("      lệch:", line)
    total = Counter()
    for c in stats.values():
        total.update(c)
    print(f"  TỔNG: khớp {total['khớp']}/{total['khớp'] + total['lệch']}")


if __name__ == "__main__":
    main()
