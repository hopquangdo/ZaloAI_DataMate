"""Chuẩn bị dữ liệu của từng doanh nghiệp một lần và dùng lại giữa các luồng."""

from __future__ import annotations

import dataclasses
import json
import threading
from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path

from datamate.infrastructure.prompt_loader import render_prompt
from datamate.modules.data.canonical import (
    Labeler,
    build_canonical,
    cached_labels,
    render_guide,
    unknown_status_values,
)
from datamate.modules.data.ingestion import Business, get_business
from datamate.modules.data.profiling import describe_business
from datamate.modules.data.semantic.capabilities import Capabilities, capabilities
from datamate.modules.data.semantic.propose import (
    Accepted,
    accept,
    apply_roles,
    parse_proposals,
    render_tables,
    role_vocabulary,
)
from datamate.modules.decision.verification import known_names
from datamate.modules.domain.business_rules import DEFAULT_SPEC, RuleSpec
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

    def __init__(
        self,
        data_dir: Path,
        cache_dir: Path | None,
        spec: RuleSpec = DEFAULT_SPEC,
        labeler: Labeler | None = None,
        role_proposer: Callable[[str], str] | None = None,
    ) -> None:
        self._spec = spec
        self._labeler = labeler
        self._role_proposer = role_proposer
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
                raw = get_business(self._data_dir / business_id, self._cache_dir)
                raw = self._with_roles(raw)
                canonical = build_canonical(raw.tables, self._spec, self._labels(raw))
                # Bảng chuẩn thay hẳn các bảng gốc nó đã chứa trọn (để bộ giải không đọc nhầm bảng
                # gốc bỏ qua trạng thái); tên và năng lực dữ liệu vẫn tính trên dữ liệu gốc.
                rest = {n: t for n, t in raw.tables.items() if n not in canonical.replaces}
                business = dataclasses.replace(raw, tables={**canonical.tables, **rest})
                guide = render_guide(canonical)
                profile = describe_business(business)
                self._ready[business_id] = PreparedBusiness(
                    business,
                    f"{guide}\n\n# Các bảng\n{profile}" if guide else profile,
                    EntityIndex(raw),
                    capabilities(raw),
                    known_names(raw),
                )
            return self._ready[business_id]

    def _with_roles(self, business: Business) -> Business:
        """Bổ sung vai trò cột do LLM đề xuất (đã kiểm chứng giá trị), lưu theo doanh nghiệp."""
        if self._role_proposer is None:
            return business
        request = render_tables(business.tables)
        if not request:
            return business
        folder = self._cache_dir or Path(".cache")
        path = folder / "column_roles" / f"{business.business_id}.json"
        if path.exists():
            accepted = Accepted.from_json(json.loads(path.read_text(encoding="utf-8")))
        else:
            vocabulary = "\n".join(f"- {r}: {d}" for r, d in role_vocabulary().items())
            prompt = render_prompt(
                "column_roles",
                roles=vocabulary,
                readme=business.readme.strip()[:3000],
                tables=request,
            )
            reply = self._role_proposer(prompt)
            if not reply:  # API lỗi: dùng luật tên cột, lần sau hỏi lại
                return business
            proposals = parse_proposals(reply, business.tables)
            accepted = accept(business.tables, proposals)
            accepted.reply = reply
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(
                json.dumps(accepted.to_json(), ensure_ascii=False, indent=1), encoding="utf-8"
            )
        return dataclasses.replace(business, tables=apply_roles(business.tables, accepted))

    def _labels(self, business: Business) -> dict[str, str]:
        """Nhãn chuẩn cho các cách ghi trạng thái lạ: hỏi LLM một lần, lưu theo doanh nghiệp."""
        unknown = unknown_status_values(business.tables)
        if not unknown or self._labeler is None:
            return {}
        folder = self._cache_dir or Path(".cache")
        path = folder / "status_labels" / f"{business.business_id}.json"
        return cached_labels(path, unknown, self._labeler)
