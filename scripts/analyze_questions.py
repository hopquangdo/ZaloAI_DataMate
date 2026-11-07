"""Phân nhóm câu hỏi train theo chủ đề + kiểu đáp án để chọn template cần viết.

Chạy: uv run python scripts/analyze_questions.py dataset/train/train
Ghi báo cáo vào reports/question_patterns.md.
"""

from __future__ import annotations

import argparse
import re
from collections import Counter, defaultdict
from pathlib import Path

from datamate.core.text import fold
from datamate.infrastructure.jsonl import read_jsonl

# Thứ tự quan trọng: chủ đề cụ thể đứng trước chủ đề chung.
TOPICS: list[tuple[str, str]] = [
    ("tet", r"\btet\b"),
    ("ca_sang_chieu", r"\bca (sang|chieu)\b"),
    ("het_han_lo", r"het han|han dung|\blo\b"),
    ("hoat_chat_ke_don", r"hoat chat|ke don"),
    ("tuoi_no", r"tuoi no|qua han|no lau"),
    ("cong_no", r"\bno\b|cong no|thu no|tra no"),
    ("ton_kho", r"\bton\b|het hang|ton kho"),
    ("nhap_hang", r"\bnhap\b|nha cung cap|\bncc\b"),
    ("lai_gia_von", r"\blai\b|\bloi\b|gia von|chi phi"),
    ("gia_ban", r"\bgia\b"),
    ("ty_le_huy_tra", r"\bhuy\b|tra hang|\btra\b"),
    ("thanh_toan", r"tien mat|chuyen khoan|\bcod\b|thanh toan"),
    ("giao_hang", r"giao|dot"),
    ("nhan_vien", r"nhan vien|\bnv\b"),
    ("khach_hang", r"\bkhach\b|\bkh\b"),
    ("xep_hang", r"nhat\b|\btop\b|nhieu nhat|it nhat|chay nhat"),
    ("so_don", r"\bdon\b"),
    ("doanh_thu", r"doanh thu|dthu|\bdt\b|ban duoc|ban dc|thu ve|tien hang|tien ban"),
    ("so_luong", r"bao nhieu|may|bnhiu|nhieu"),
]

MEASURES: list[tuple[str, str]] = [
    ("phan_tram_thay_doi", r"thay doi|tang truong|tang bao nhieu %|giam bao nhieu %"),
    ("chenh_lech", r"chenh|hon|kem|tang|giam"),
    ("ty_trong", r"ti trong|ty trong|chiem"),
    ("trung_binh", r"trung binh|binh quan|\btb\b"),
]

PERIODS: list[tuple[str, str]] = [
    ("hom_nay", r"hom nay"),
    ("hom_qua", r"hom qua"),
    ("tuan_nay", r"tuan nay"),
    ("tuan_truoc", r"tuan (truoc|roi)"),
    ("thang_nay", r"thang nay"),
    ("thang_truoc", r"thang (truoc|roi)"),
    ("n_ngay", r"\d+ ngay"),
    ("tu_dau_nam", r"dau nam"),
    ("quy", r"\bquy\b"),
    ("thang_cu_the", r"thang \d{1,2}"),
    ("ngay_cu_the", r"\d{1,2}/\d{1,2}/\d{4}|ngay \d"),
    ("den_het", r"den het|tinh den"),
]


def first_match(text: str, rules: list[tuple[str, str]], default: str) -> str:
    return next((name for name, pattern in rules if re.search(pattern, text)), default)


def business_industries(data_dir: Path) -> dict[str, str]:
    """Đoán ngành từ README để thống kê theo ngành (chỉ phục vụ phân tích)."""
    keywords = {
        "nha_thuoc": "thuoc",
        "ca_phe": "ca phe",
        "vlxd": "vat lieu|xi mang|gach",
        "tap_hoa": "tap hoa|nuoc ngot|mi ",
    }
    result = {}
    for readme in data_dir.glob("*/README.md"):
        text = fold(readme.read_text(encoding="utf-8"))
        result[readme.parent.name] = first_match(text, list(keywords.items()), "khac")
    return result


def build_report(split_dir: Path) -> str:
    questions = list(read_jsonl(split_dir / "questions.jsonl"))
    answers = {a["id"]: a for a in read_jsonl(split_dir / "answers.jsonl")}
    industries = business_industries(split_dir / "data")

    pattern_counts: Counter[tuple[str, str, str]] = Counter()
    examples: dict[tuple[str, str, str], list[str]] = defaultdict(list)
    periods: Counter[str] = Counter()
    by_industry: Counter[str] = Counter()

    for question in questions:
        text = fold(question["question"])
        key = (
            first_match(text, TOPICS, "khac"),
            first_match(text, MEASURES, "gia_tri"),
            answers[question["id"]]["type"],
        )
        pattern_counts[key] += 1
        if len(examples[key]) < 2:
            examples[key].append(question["question"])
        periods[first_match(text, PERIODS, "khong_ro")] += 1
        by_industry[industries.get(question["business_id"], "khac")] += 1

    total = len(questions)
    lines = [
        "# Phân tích mẫu câu hỏi (train)",
        "",
        f"Tổng: {total} câu, {len(industries)} doanh nghiệp.",
        "",
        "## Theo ngành (đoán từ README)",
        "",
        *[f"- {name}: {count}" for name, count in by_industry.most_common()],
        "",
        "## Theo cách nói thời gian",
        "",
        *[f"- {name}: {count}" for name, count in periods.most_common()],
        "",
        "## Mẫu (chủ đề × phép đo × kiểu đáp án)",
        "",
        "| # | Chủ đề | Phép đo | Kiểu | N | Lũy kế % | Ví dụ |",
        "|---|---|---|---|---|---|---|",
    ]
    cumulative = 0
    for rank, (key, count) in enumerate(pattern_counts.most_common(), start=1):
        cumulative += count
        sample = " / ".join(examples[key]).replace("|", "\\|")
        lines.append(
            f"| {rank} | {key[0]} | {key[1]} | {key[2]} | {count} | "
            f"{100 * cumulative / total:.1f} | {sample} |"
        )
    return "\n".join(lines) + "\n"


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("split_dir", type=Path)
    parser.add_argument("--out", type=Path, default=Path("reports/question_patterns.md"))
    args = parser.parse_args()
    report = build_report(args.split_dir)
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(report, encoding="utf-8")
    print(f"Đã ghi {args.out}")


if __name__ == "__main__":
    main()
