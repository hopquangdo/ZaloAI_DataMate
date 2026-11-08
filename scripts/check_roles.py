"""Đo LLM đề xuất vai trò cột: độ phủ bảng chuẩn và độ khớp đáp án train, có/không làm nhiễu tên cột.

Bốn cách chạy trên mỗi doanh nghiệp:
  code     : luật tên cột như cũ;
  llm      : thêm vai trò do LLM đề xuất (đã kiểm chứng giá trị);
  p-code   : tên cột bị đổi sang cách viết lạ (làm nhiễu), chỉ luật tên cột;
  p-llm    : tên cột bị đổi, có LLM đề xuất.
So sánh với đáp án chuẩn bằng các câu đơn giản của scripts/check_canonical.py.

    uv run python scripts/check_roles.py [--only biz_101 biz_102 ...]
"""

from __future__ import annotations

import argparse
import json
import sys
from collections import Counter, defaultdict
from datetime import date
from functools import partial
from pathlib import Path

import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent))
import check_canonical as cc  # noqa: E402

from datamate.app.business_registry import BusinessRegistry  # noqa: E402
from datamate.app.pipeline import _propose_roles  # noqa: E402
from datamate.core.text import fold  # noqa: E402
from datamate.infrastructure.config import LLMSettings  # noqa: E402
from datamate.infrastructure.llm import LLMClient  # noqa: E402
from datamate.modules.data.canonical import build_canonical  # noqa: E402
from datamate.modules.data.ingestion import Business, get_business  # noqa: E402
from datamate.modules.data.semantic import classify, column_roles  # noqa: E402
from datamate.modules.understanding.normalize import time_hints  # noqa: E402

# Cách viết lạ cho từng vai trò (xác nhận luật tên cột không nhận ra mới đổi).
ALIASES = {
    "order_id": "SoCT_k",
    "event_date": "Ngay_GD",
    "line_amount": "TT_vnd",
    "qty": "SL_ban",
    "unit_price": "DG_vnd",
    "status": "GhiChuXL",
    "product": "Hang_ban_ra",
    "customer_code": "KH_id",
    "payment": "PTTT_x",
    "receipt_amount": "So_tien_thu",
    "receipt_date": "Ngay_TT",
    "qty_base": "SL_goc",
    "cost_price": "GV_dv",
}


def perturb(business: Business) -> Business:
    """Đổi tên các cột có vai trò quan trọng sang cách viết lạ; giữ nguyên dữ liệu."""
    import dataclasses

    tables: dict[str, pd.DataFrame] = {}
    renamed: dict[str, str] = {}
    for name, table in business.tables.items():
        rename: dict[str, str] = {}
        taken: set[str] = set(map(str, table.columns))
        for column, hint in column_roles(table).items():
            alias = ALIASES.get(hint.role)
            if alias and alias not in taken and classify(alias) is None:
                rename[column] = alias
                taken.add(alias)
        renamed.update(rename)
        tables[name] = table.rename(columns=rename) if rename else table
    readme = business.readme
    for old, new in renamed.items():  # README cũng phải khớp tên cột mới, như dữ liệu thật
        readme = readme.replace(old, new)
    return dataclasses.replace(business, tables=tables, readme=readme)


def coverage(canon: dict[str, pd.DataFrame]) -> dict[str, float]:
    lines, orders = canon.get("dong_hang_chuan"), canon.get("don_chuan")
    out = {"đơn": float(orders is not None), "dòng": float(lines is not None)}
    out["tên hàng"] = float(lines["Tên hàng"].notna().mean()) if lines is not None else 0.0
    out["trạng thái"] = (
        float(orders["Trạng thái chuẩn"].notna().mean()) if orders is not None else 0.0
    )
    out["công nợ"] = float("thanh_toan_chuan" in canon)
    return out


def evaluate(
    questions: list[dict], answers: dict[str, dict], canon: dict[str, pd.DataFrame]
) -> Counter[str]:
    stats: Counter[str] = Counter()
    for q in questions:
        ref = answers.get(q["id"])
        kind = cc._kind(fold(q["question"]))
        if kind is None or ref is None or ref["type"] not in {"number", "percent"}:
            continue
        hints = time_hints(q["question"], date.fromisoformat(q["as_of_date"]))
        if len(hints) != 1:
            continue
        try:
            pred = cc._predict(kind, canon, hints[0].period.start, hints[0].period.end)
        except (KeyError, ValueError):
            pred = None
        if pred is None:
            stats["thiếu"] += 1
            continue
        tolerance = 0.006 if kind == "cancel_rate" else 0.5
        stats["ok" if abs(pred - float(ref["answer"])) <= tolerance else "bad"] += 1
    return stats


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--only", nargs="*", default=None)
    parser.add_argument("--cache", default=".cache/roles_check")
    args = parser.parse_args()
    split = cc.SPLIT
    questions = [json.loads(x) for x in (split / "questions.jsonl").read_text(encoding="utf-8").splitlines() if x.strip()]
    answers = {a["id"]: a for a in (json.loads(x) for x in (split / "answers.jsonl").read_text(encoding="utf-8").splitlines() if x.strip())}
    by_biz: dict[str, list[dict]] = defaultdict(list)
    for q in questions:
        by_biz[q["business_id"]].append(q)

    llm = LLMClient(LLMSettings.from_env())
    registry_p = partial(_propose_roles, llm)
    totals: dict[str, Counter[str]] = {v: Counter() for v in ("code", "llm", "p-code", "p-llm")}
    cover: dict[str, Counter[str]] = {v: Counter() for v in totals}
    accepted_total = Counter()
    for biz in sorted(by_biz):
        if args.only and biz not in args.only:
            continue
        raw = get_business(split / "data" / biz, Path(".cache/businesses"))
        variants = {"code": raw, "p-code": perturb(raw)}
        for tag, base in (("llm", raw), ("p-llm", variants["p-code"])):
            registry = BusinessRegistry(
                split / "data", Path(args.cache) / tag, role_proposer=registry_p
            )
            variants[tag] = registry._with_roles(base)
            n = sum(len(t.attrs.get("column_roles_override", {})) for t in variants[tag].tables.values())
            accepted_total[tag] += n
        row = []
        for tag in ("code", "llm", "p-code", "p-llm"):
            canon = build_canonical(variants[tag].tables).tables
            stats = evaluate(by_biz[biz], answers, canon)
            totals[tag].update(stats)
            for k, v in coverage(canon).items():
                cover[tag][k] += v
            row.append(f"{tag}: {stats['ok']}/{stats['ok'] + stats['bad']}")
        print(biz, " | ".join(row), flush=True)
    print()
    for tag, c in totals.items():
        n = c["ok"] + c["bad"]
        print(f"{tag:7s} khớp {c['ok']}/{n} ({100 * c['ok'] / max(n, 1):.0f}%), thiếu {c['thiếu']}; "
              f"độ phủ tổng {dict(cover[tag])}; vai trò LLM được nhận {accepted_total.get(tag, 0)}")


if __name__ == "__main__":
    main()
