"""Chuẩn bị dữ liệu của từng doanh nghiệp một lần và dùng lại giữa các luồng."""

from __future__ import annotations

import threading
from dataclasses import dataclass
from pathlib import Path

from datamate.modules.data.ingestion import Business, get_business
from datamate.modules.data.profiling import describe_business
from datamate.modules.data.semantic.capabilities import Capabilities, capabilities
from datamate.modules.decision.verification import known_names
from datamate.modules.understanding.normalize import EntityIndex


@dataclass(frozen=True)
class PreparedBusiness:
    """Dữ liệu một doanh nghiệp đã sẵn sàng để hỏi: bảng, mô tả bảng, chỉ mục tên."""

    business: Business
    profile: str  # mô tả bảng đưa vào prompt
    entities: EntityIndex  # chỉ mục tên hàng/khách/nhóm để khớp với câu hỏi
    capabilities: Capabilities  # loại thông tin shop có ghi, khoảng ngày (luật unanswerable)
    names: frozenset[str]  # mọi giá trị chữ đã chuẩn hoá (kiểm tra tên trong đáp án)


class BusinessRegistry:
    """Mỗi doanh nghiệp được chuẩn bị đúng một lần; chỉ luồng cùng doanh nghiệp chờ nhau."""

    def __init__(self, data_dir: Path, cache_dir: Path | None) -> None:
        self._data_dir = data_dir
        self._cache_dir = cache_dir
        self._ready: dict[str, PreparedBusiness] = {}
        self._locks: dict[str, threading.Lock] = {}
        self._guard = threading.Lock()

    def get(self, business_id: str) -> PreparedBusiness:
        with self._guard:
            lock = self._locks.setdefault(business_id, threading.Lock())
        with lock:
            if business_id not in self._ready:
                business = get_business(self._data_dir / business_id, self._cache_dir)
                self._ready[business_id] = PreparedBusiness(
                    business,
                    describe_business(business),
                    EntityIndex(business),
                    capabilities(business),
                    known_names(business),
                )
            return self._ready[business_id]
