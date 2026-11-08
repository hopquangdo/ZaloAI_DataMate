"""Kiểm tra bảng chuẩn tắc trên train: dựng cho mọi doanh nghiệp rồi đối chiếu đáp án chuẩn.

Với các câu đơn giản theo MỘT khoảng thời gian rõ ràng (doanh thu, số đơn, số đơn huỷ, tỉ lệ huỷ),
tính lại từ bảng chuẩn tắc và so với đáp án chuẩn. Không gọi LLM: chỉ để biết bảng chuẩn tắc đúng
đến đâu trước khi đưa cho LLM dùng.

    uv run python scripts/check_canonical.py [--show-mismatch N]
"""

from __future__ import annotations

import argparse
import json
import re
from collections import Counter, defaultdict
from datetime import date
from pathlib import Path

import pandas as pd

from datamate.core.text import fold
from datamate.modules.data.canonical import LINES, ORDERS, build_canonical
from datamate.modules.data.ingestion import get_business
from datamate.modules.understanding.normalize import time_hints

SPLIT = Path("dataset/train/train")
EXTRA = re.compile(
    r"nhom|khach|nhan vien|\bnv\b|so voi|trung binh|binh quan|tien mat|chuyen khoan|cod|quay|"
    r"zalo|online|ca sang|ca chieu|hang|mon|san pham|ngay nao|thu may|cao nhat|thap nhat|top|"
    r"lai|von|no |nhap|ton|cong|size|loai|nhom|tuan|quy|%|phan tram|ti trong|chiem"
)


def _kind(folded: str) -> str | None:
    if EXTRA.search(folded.replace("ti le huy", "").replace("don huy", "")):
        if "ti le huy" in folded or "ty le huy" in folded:
            pass
        else:
            return None
    if re.search(r"t[iy] le (don )?huy|bao nhieu % don bi huy|phan tram don", folded):
        return "cancel_rate"
    if re.search(r"(bao nhieu|may|so) (don|bill|hoa don).*huy|huy.*(bao nhieu|may) (don|bill)", folded):
        return "cancel_count"
    if re.search(r"bao nhieu don|may don|so don", folded):
        return "order_count"
    if re.search(r"doanh thu|dthu|tien ban|ban duoc bao nhieu tien", folded):
        return "revenue"
    return None


def _predict(  # noqa: PLR0911
    kind: str, canon: dict[str, pd.DataFrame], start: date, end: date
) -> float | None:
    if ORDERS not in canon:  # sổ bán hàng không có mã đơn: chỉ tính được doanh thu
        if kind != "revenue":
            return None
        lines = canon[LINES]
        in_range = lines[(lines["Ngày đặt"].dt.normalize() >= pd.Timestamp(start))
                         & (lines["Ngày đặt"].dt.normalize() <= pd.Timestamp(end))]
        return float(in_range[in_range["Tính vào doanh thu"]]["Thành tiền dòng"].sum())
    orders = canon[ORDERS]
    day = orders["Ngày đặt"].dt.normalize()
    inside = orders[(day >= pd.Timestamp(start)) & (day <= pd.Timestamp(end))]
    counted = inside[inside["Tính vào doanh thu"]]
    if kind == "revenue":
        return float(counted["Doanh thu đơn"].sum())
    if kind == "order_count":
        return float(len(counted))
    if kind == "cancel_count":
        return float((inside["Trạng thái chuẩn"] == "huy").sum())
    if kind == "cancel_rate":
        return round(100 * float((inside["Trạng thái chuẩn"] == "huy").sum()) / len(inside), 2) if len(inside) else None
    return None


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--show-mismatch", type=int, default=12)
    args = parser.parse_args()

    questions = [json.loads(x) for x in (SPLIT / "questions.jsonl").read_text(encoding="utf-8").splitlines() if x.strip()]
    answers = {a["id"]: a for a in (json.loads(x) for x in (SPLIT / "answers.jsonl").read_text(encoding="utf-8").splitlines() if x.strip())}
    by_biz: dict[str, list[dict]] = defaultdict(list)
    for q in questions:
        by_biz[q["business_id"]].append(q)

    built, missing = 0, []
    stats: dict[str, Counter[str]] = defaultdict(Counter)
    mismatches: list[str] = []
    for biz in sorted(by_biz):
        business = get_business(SPLIT / "data" / biz, Path(".cache/businesses"))
        canon = build_canonical(business.tables)
        if not canon.tables:
            missing.append(f"{biz}: {'; '.join(canon.notes)}")
            continue
        built += 1
        for q in by_biz[biz]:
            ref = answers.get(q["id"])
            folded = fold(q["question"])
            kind = _kind(folded)
            if kind is None or ref is None or ref["type"] not in {"number", "percent"}:
                continue
            hints = time_hints(q["question"], date.fromisoformat(q["as_of_date"]))
            if len(hints) != 1:
                continue
            pred = _predict(kind, canon.tables, hints[0].period.start, hints[0].period.end)
            if pred is None:
                continue
            ok = abs(pred - float(ref["answer"])) <= (0.006 if kind == "cancel_rate" else 0.5)
            stats[biz]["ok" if ok else "bad"] += 1
            stats["_all"]["ok" if ok else "bad"] += 1
            if not ok:
                mismatches.append(f"[{biz}] {kind}: {q['question'][:70]} | chuẩn={ref['answer']} | bảng chuẩn={pred}")
    print(f"dựng được bảng chuẩn tắc cho {built}/{len(by_biz)} doanh nghiệp")
    for line in missing:
        print("  KHÔNG dựng được:", line)
    for biz, c in sorted(stats.items()):
        total = c["ok"] + c["bad"]
        print(f"  {biz}: khớp {c['ok']}/{total}")
    for line in mismatches[: args.show_mismatch]:
        print("  lệch:", line)


if __name__ == "__main__":
    main()
