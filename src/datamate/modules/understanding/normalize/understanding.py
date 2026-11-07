"""Gộp các phân tích câu hỏi (viết lại, thời gian, thực thể) thành khối gợi ý cho prompt."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date

from datamate.modules.understanding.normalize.entities import EntityHit, EntityIndex
from datamate.modules.understanding.normalize.normalize import normalize_question
from datamate.modules.understanding.normalize.time_hints import TimeHint, time_hints

_HEADER = "# Gợi ý từ phân tích câu hỏi (do code tính, tin cậy hơn tự suy đoán)"


@dataclass(frozen=True, slots=True)
class Understanding:
    """Kết quả hiểu câu hỏi: câu viết lại, gợi ý thời gian, tên trong dữ liệu."""

    normalized: str
    time: list[TimeHint]
    entities: list[EntityHit]

    def render(self, original: str) -> str:
        """Khối gợi ý đưa vào prompt; chuỗi rỗng nếu không có gì đáng nói."""
        lines: list[str] = []
        if self.normalized != " ".join(original.split()):
            lines.append(f"Câu hỏi viết lại đầy đủ: {self.normalized}")
        lines += [f"Thời gian: {hint.render()}" for hint in self.time]
        for hit in self.entities:
            values = " | ".join(repr(v) for v in hit.values)
            lines.append(
                f'Tên trong dữ liệu: "{hit.phrase}" → T["{hit.table}"]["{hit.column}"] = {values}'
            )
        return f"{_HEADER}\n" + "\n".join(lines) if lines else ""


def understand(question: str, today: date, entities: EntityIndex) -> Understanding:
    """Phân tích một câu hỏi trên dữ liệu của doanh nghiệp."""
    return Understanding(
        normalized=normalize_question(question),
        time=time_hints(question, today),
        entities=entities.find(question),
    )
