"""Ghi lại cấu hình của một lượt chạy (run_meta.json) để so sánh các lượt chạy với nhau.

Chỉ ghi thứ cần để tái lập và đối chiếu: model, tham số, số câu, thời gian, phiên bản code. Không
ghi khoá API.
"""

from __future__ import annotations

import dataclasses
import hashlib
import platform
import subprocess
import sys
import time
from datetime import datetime
from pathlib import Path
from typing import Any

from datamate.infrastructure.config import LLMSettings
from datamate.modules.decision.consensus import ConsensusSettings
from datamate.modules.solvers.pandas import AgentSettings

_PACKAGE_DIR = Path(__file__).resolve().parents[1]


def code_fingerprint() -> str:
    """Băm mã nguồn và prompt: hai lượt chạy cùng mã thì có cùng giá trị (không cần git)."""
    digest = hashlib.sha1()
    for path in sorted(_PACKAGE_DIR.rglob("*")):
        if path.suffix in {".py", ".md", ".tsv", ".txt"} and "__pycache__" not in path.parts:
            digest.update(str(path.relative_to(_PACKAGE_DIR)).encode())
            digest.update(path.read_bytes())
    return digest.hexdigest()[:12]


def _git_commit() -> str | None:
    try:
        out = subprocess.run(
            ["git", "rev-parse", "--short", "HEAD"],
            capture_output=True,
            text=True,
            timeout=5,
            cwd=_PACKAGE_DIR,
            check=False,
        )
    except (OSError, subprocess.SubprocessError):
        return None
    return out.stdout.strip() or None


def build_manifest(
    *,
    args: dict[str, Any],
    llm: LLMSettings,
    agent: AgentSettings,
    consensus: ConsensusSettings,
    questions: int,
) -> dict[str, Any]:
    """Bản ghi mô tả lượt chạy; ``finish_manifest`` bổ sung kết quả khi chạy xong."""
    llm_info = {k: v for k, v in dataclasses.asdict(llm).items() if k != "api_key"}
    return {
        "started_at": datetime.now().astimezone().isoformat(timespec="seconds"),
        "code": {"fingerprint": code_fingerprint(), "git_commit": _git_commit()},
        "args": {k: str(v) if isinstance(v, Path) else v for k, v in args.items()},
        "llm": llm_info,
        "agent": dataclasses.asdict(agent),
        "consensus": dataclasses.asdict(consensus),
        "questions": questions,
        "environment": {"python": sys.version.split()[0], "platform": platform.platform()},
        "_t0": time.perf_counter(),
    }


def finish_manifest(
    manifest: dict[str, Any], errors: dict[str, int], completed: int
) -> dict[str, Any]:
    """Thêm kết quả tổng quát: thời gian chạy, số câu xong, lỗi theo loại."""
    started = manifest.pop("_t0", time.perf_counter())
    return {
        **manifest,
        "finished_at": datetime.now().astimezone().isoformat(timespec="seconds"),
        "seconds": round(time.perf_counter() - started, 1),
        "completed": completed,
        "errors": dict(errors),
    }
