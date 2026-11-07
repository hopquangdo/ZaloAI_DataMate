"""Cache doanh nghiệp đã nạp: trong bộ nhớ (theo tiến trình) và trên đĩa (pickle).

Khoá cache gồm tên, kích thước, mtime của từng file và phiên bản ingestion, nên đổi
dữ liệu hoặc đổi code làm sạch đều làm cache cũ mất hiệu lực.
"""

from __future__ import annotations

import functools
import hashlib
import pickle
import threading
from pathlib import Path

from datamate.core import text as text_module
from datamate.modules.data.ingestion.business import Business, load_business


@functools.cache
def ingestion_version() -> str:
    """Băm mã nguồn ingestion: đổi code làm sạch thì cache cũ tự mất hiệu lực, khỏi bump tay.

    Tính lần đầu cần (không đọc file lúc import) rồi nhớ lại.
    """
    sources = [
        *sorted(Path(__file__).parent.glob("*.py")),
        Path(text_module.__file__),
    ]
    digest = hashlib.sha1()
    for path in sources:
        digest.update(path.name.encode())
        digest.update(path.read_bytes())
    return digest.hexdigest()[:8]


_memory: dict[Path, Business] = {}
_locks: dict[Path, threading.Lock] = {}
_registry_lock = threading.Lock()


def _fingerprint(directory: Path) -> str:
    digest = hashlib.sha1(ingestion_version().encode())
    for path in sorted(directory.iterdir()):
        stat = path.stat()
        digest.update(f"{path.name}:{stat.st_size}:{stat.st_mtime_ns}".encode())
    return digest.hexdigest()[:16]


def _load_from_disk(directory: Path, cache_dir: Path) -> Business:
    target = cache_dir / f"{directory.name}-{_fingerprint(directory)}.pkl"
    if target.exists():
        try:
            with target.open("rb") as file:
                cached: Business = pickle.load(file)
                return cached
        except (pickle.UnpicklingError, EOFError, AttributeError, ImportError):
            target.unlink(missing_ok=True)  # cache hỏng/cũ: nạp lại từ dữ liệu gốc
    business = load_business(directory)
    cache_dir.mkdir(parents=True, exist_ok=True)
    temporary = target.with_suffix(".tmp")
    with temporary.open("wb") as file:
        pickle.dump(business, file, protocol=pickle.HIGHEST_PROTOCOL)
    temporary.replace(target)
    return business


def get_business(directory: Path, cache_dir: Path | None) -> Business:
    """Nạp một lần cho mỗi doanh nghiệp, an toàn khi nhiều luồng cùng gọi."""
    directory = directory.resolve()
    with _registry_lock:
        lock = _locks.setdefault(directory, threading.Lock())
    with lock:
        if directory not in _memory:
            _memory[directory] = (
                load_business(directory)
                if cache_dir is None
                else _load_from_disk(directory, cache_dir)
            )
        return _memory[directory]
