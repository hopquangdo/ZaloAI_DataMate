"""Runner (CLI/batch): chạy pipeline trên một tập câu hỏi, ghi submission.jsonl từng dòng khi xong.

Ví dụ:
    uv run python -m datamate.app.runner dataset/train/train --limit 50 --workers 8
    uv run python -m datamate.app.runner /data --out /result/submission.jsonl  # trong Docker

Chính sách lỗi: lỗi gọi API chỉ làm lần sinh đó bị bỏ qua (Pipeline xử lý). Lỗi chương trình ở
một câu được ghi rõ (kèm traceback) và câu đó abstain để không mất cả lượt; cuối lượt có tổng
kết. Dùng ``--strict`` khi phát triển để dừng ngay ở lỗi đầu tiên.
"""

from __future__ import annotations

import argparse
import logging
import random
import time
import traceback
from collections import Counter
from collections.abc import Collection
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path

from datamate.app.pipeline import Pipeline, Result
from datamate.app.question import Question
from datamate.app.run_log import RunLog
from datamate.infrastructure.config import LLMSettings
from datamate.infrastructure.jsonl import JsonlWriter, read_jsonl
from datamate.infrastructure.llm import LLMClient
from datamate.modules.decision.consensus import ConsensusSettings
from datamate.modules.domain.answer import ABSTAIN
from datamate.modules.solvers.pandas import AgentSettings

log = logging.getLogger("datamate")

_PROGRESS_EVERY = 10
# Bao nhiêu câu liên tiếp lỗi API thì coi như LLM đã chết (hết tiền, server sập) và dừng lượt chạy.
DEAD_LLM_STREAK = 20


def select_questions(  # noqa: PLR0913
    questions: list[Question],
    *,
    businesses: Collection[str] = (),
    ids: Collection[str] = (),
    limit: int = 0,
    seed: int = 0,
    done: Collection[str] = (),
) -> list[Question]:
    """Lọc theo doanh nghiệp/id, lấy mẫu `limit` câu (cố định theo `seed`), bỏ câu đã làm."""
    if businesses:
        questions = [q for q in questions if q.business_id in businesses]
    if ids:
        questions = [q for q in questions if q.id in ids]
    if limit and limit < len(questions):
        questions = random.Random(seed).sample(questions, limit)
    # Gom theo business: các câu cùng doanh nghiệp chạy liền nhau
    return sorted((q for q in questions if q.id not in done), key=lambda q: q.business_id)


def answer_safely(pipeline: Pipeline, question: Question, *, strict: bool = False) -> Result:
    """Chạy một câu; lỗi chương trình thành abstain có log đầy đủ, trừ khi ``strict``."""
    try:
        return pipeline.answer(question)
    except Exception as exc:
        if strict:
            raise
        log.error("Lỗi chương trình ở câu %s: %s", question.id, exc, exc_info=True)
        return Result(ABSTAIN, RunLog.failure(question, exc, traceback.format_exc()))


def _llm_dead(result: Result) -> bool:
    """Câu không có lần sinh nào chạy được vì lỗi API (không phải vì model trả lời abstain)."""
    log_ = result.log
    return log_.error_kind == "api" and log_.attempts == 0


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Chạy DataMate agent.")
    parser.add_argument(
        "split_dir", type=Path, help="thư mục có questions.jsonl, data/, rulebook.md"
    )
    parser.add_argument("--out", type=Path, default=Path("reports/submission.jsonl"))
    parser.add_argument("--log", type=Path, default=Path("reports/run_log.jsonl"))
    parser.add_argument("--cache-dir", type=Path, default=Path(".cache/businesses"))
    parser.add_argument(
        "--limit", type=int, default=0, help="lấy mẫu ngẫu nhiên N câu (0 = tất cả)"
    )
    parser.add_argument("--seed", type=int, default=0)
    parser.add_argument("--business", nargs="*", default=[])
    parser.add_argument("--ids", nargs="*", default=[])
    parser.add_argument("--workers", type=int, default=8)
    parser.add_argument("--resume", action="store_true", help="bỏ qua câu đã có trong --out")
    parser.add_argument("--strict", action="store_true", help="dừng ngay khi có lỗi chương trình")
    return parser.parse_args()


def _load_questions(args: argparse.Namespace) -> list[Question]:
    questions = [Question.from_record(r) for r in read_jsonl(args.split_dir / "questions.jsonl")]
    done = {r["id"] for r in read_jsonl(args.out)} if args.resume else set()
    return select_questions(
        questions,
        businesses=frozenset(args.business),
        ids=frozenset(args.ids),
        limit=args.limit,
        seed=args.seed,
        done=done,
    )


def _build_pipeline(args: argparse.Namespace) -> Pipeline:
    return Pipeline(
        args.split_dir,
        args.cache_dir,
        LLMClient(LLMSettings.from_env()),
        AgentSettings.from_env(),
        ConsensusSettings.from_env(),
    )


def _run(pipeline: Pipeline, questions: list[Question], args: argparse.Namespace) -> Counter[str]:
    """Chạy cả danh sách bằng nhiều luồng, ghi kết quả ngay khi xong; trả số câu lỗi theo loại."""
    errors: Counter[str] = Counter()
    submission, run_log = JsonlWriter(args.out), JsonlWriter(args.log)
    started = time.perf_counter()
    log.info("Chạy %d câu với %d luồng…", len(questions), args.workers)
    try:
        with ThreadPoolExecutor(max_workers=args.workers) as pool:
            futures = [
                pool.submit(answer_safely, pipeline, q, strict=args.strict) for q in questions
            ]
            streak = 0
            for index, future in enumerate(as_completed(futures), start=1):
                result = future.result()
                streak = streak + 1 if _llm_dead(result) else 0
                if streak >= DEAD_LLM_STREAK:
                    pool.shutdown(wait=False, cancel_futures=True)
                    errors["llm_dead"] += 1
                    log.error(
                        "%d câu liên tiếp lỗi API: dừng lượt chạy (các câu này không được ghi). "
                        "Sửa LLM rồi chạy lại với --resume.",
                        streak,
                    )
                    break
                if _llm_dead(result):
                    continue  # chưa ghi: --resume sẽ chạy lại câu này
                submission.write(result.record)
                run_log.write(result.log.to_record())
                if result.log.error_kind:
                    errors[result.log.error_kind] += 1
                if index % _PROGRESS_EVERY == 0 or index == len(futures):
                    log.info("  %d/%d  %.0fs", index, len(futures), time.perf_counter() - started)
    finally:
        submission.close()
        run_log.close()
    return errors


def _report(errors: Counter[str], args: argparse.Namespace) -> None:
    if errors:
        log.warning(
            "Có %d câu lỗi chương trình và %d câu lỗi gọi API; chi tiết trong %s",
            errors["bug"],
            errors["api"],
            args.log,
        )
    answers_path = args.split_dir / "answers.jsonl"
    if answers_path.exists():
        log.info("Chấm điểm: uv run python -m eval %s %s --only-answered", args.out, answers_path)


def main() -> None:
    """Điểm vào CLI: đọc tham số, chạy cả tập, ghi kết quả và tổng kết lỗi."""
    logging.basicConfig(level=logging.INFO, format="%(message)s")
    args = _parse_args()
    if not args.resume:
        for path in (args.out, args.log):
            path.unlink(missing_ok=True)
    questions = _load_questions(args)
    errors = _run(_build_pipeline(args), questions, args)
    _report(errors, args)


if __name__ == "__main__":
    main()
