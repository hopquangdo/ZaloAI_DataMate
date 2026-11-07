"""Chia doanh nghiệp của một tập thành phần tinh chỉnh (dev) và phần giữ riêng (holdout).

Test riêng của đề là doanh nghiệp MỚI, nên chỉ đo trên holdout mới biết hệ thống có tổng quát
không. Chia theo doanh nghiệp (không theo câu), cố định theo seed.

Chạy: uv run python -m eval.holdout dataset/train/train --fraction 0.3
In ra lệnh chạy cho từng phần (dùng --business của runner).
"""

from __future__ import annotations

import argparse
import random
from pathlib import Path


def split(businesses: list[str], fraction: float, seed: int) -> tuple[list[str], list[str]]:
    shuffled = sorted(businesses)
    random.Random(seed).shuffle(shuffled)
    cut = max(1, round(len(shuffled) * fraction))
    return sorted(shuffled[cut:]), sorted(shuffled[:cut])


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("split_dir", type=Path)
    parser.add_argument("--fraction", type=float, default=0.3, help="tỉ lệ doanh nghiệp giữ riêng")
    parser.add_argument("--seed", type=int, default=2026)
    args = parser.parse_args()
    names = [p.name for p in (args.split_dir / "data").iterdir() if p.is_dir()]
    dev, holdout = split(names, args.fraction, args.seed)
    print(f"dev ({len(dev)}): {' '.join(dev)}")
    print(f"holdout ({len(holdout)}): {' '.join(holdout)}")
    print(
        f"\nuv run python -m datamate {args.split_dir} --business {' '.join(holdout)} "
        "--out reports/holdout.jsonl --log reports/holdout_log.jsonl"
    )


if __name__ == "__main__":
    main()
