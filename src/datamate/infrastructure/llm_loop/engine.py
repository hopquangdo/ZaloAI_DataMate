"""Giao diện mà mỗi bộ giải cắm vào vòng lặp: Engine (chạy code) và Check (soát kết quả).

Vòng lặp không biết code là Python hay SQL, cũng không biết kết quả là đáp án theo đề hay đặc tả
JSON: những điều đó do Engine quyết định. Nhờ vậy cùng một vòng dùng được cho mọi tầng.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Any, Literal, Protocol

if TYPE_CHECKING:
    from datamate.infrastructure.llm_loop.state import LoopState

CheckKind = Literal["rule", "llm"]


class AttemptError(Exception):
    """Lượt này hỏng (không có code, bị chặn, lỗi chạy, sai format); thông điệp là feedback."""


class Engine(Protocol):
    """Phần riêng của từng bộ giải."""

    language: str  # tên khối code mà LLM phải viết: "python", "sql", "json"

    def extract(self, reply: str) -> str | None:
        """Lấy code từ câu trả lời của LLM; None nếu không thấy."""
        ...

    def run(self, code: str) -> Any:
        """Chạy code, trả kết quả ứng viên; lượt hỏng thì raise AttemptError(feedback)."""
        ...

    def describe(self, candidate: Any) -> dict[str, Any]:
        """Kết quả ở dạng JSON thuần để ghi nhật ký."""
        ...


@dataclass(frozen=True)
class CheckResult:
    """Kết quả một lượt soát. ``feedback`` là None nghĩa là đạt (vẫn ghi token và nhật ký)."""

    feedback: str | None
    names: list[str] = field(default_factory=list)  # tên luật đã bắn (để không bắn lại)
    tokens: int = 0  # token Check đã dùng (nếu gọi LLM)
    trace: dict[str, Any] = field(default_factory=dict)

    @property
    def rejected(self) -> bool:
        return self.feedback is not None


class Check(Protocol):
    """Soát kết quả ứng viên sau khi chạy được.

    ``kind="llm"`` là check tốn thêm lượt gọi LLM; nếu hết lượt mà check loại này vẫn bác thì
    vòng lặp không trả kết quả (abstain), vì bị một bên soát độc lập bác đến cùng là tín hiệu xấu.
    Check ``kind="rule"`` chỉ là nhắc nhở: hết lượt thì vẫn giữ kết quả hợp lệ gần nhất.
    """

    name: str
    kind: CheckKind

    def __call__(self, state: LoopState) -> CheckResult | None:
        """None hoặc CheckResult(feedback=None) là đạt."""
        ...
