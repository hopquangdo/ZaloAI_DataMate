"""Đọc và ghi file JSON Lines (mỗi dòng một bản ghi)."""

from __future__ import annotations

import json
import threading
from collections.abc import Iterator
from pathlib import Path
from typing import Any


def read_jsonl(path: Path) -> Iterator[dict[str, Any]]:
    """Các bản ghi trong file; file không tồn tại thì không có bản ghi nào."""
    if not path.exists():
        return
    with path.open(encoding="utf-8") as file:
        for line in file:
            if line.strip():
                yield json.loads(line)


class JsonlWriter:
    """Ghi thêm từng dòng và flush ngay: dừng giữa chừng vẫn giữ được phần đã xong."""

    def __init__(self, path: Path) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        self._file = path.open("a", encoding="utf-8")
        self._lock = threading.Lock()

    def write(self, record: dict[str, Any]) -> None:
        line = json.dumps(record, ensure_ascii=False, default=str)
        with self._lock:
            self._file.write(line + "\n")
            self._file.flush()

    def close(self) -> None:
        self._file.close()
