"""Hiểu câu hỏi bằng code: chuẩn hoá viết tắt, quy đổi thời gian, khớp thực thể trong dữ liệu."""

from datamate.modules.understanding.normalize.entities import EntityHit, EntityIndex
from datamate.modules.understanding.normalize.normalize import normalize_question
from datamate.modules.understanding.normalize.time_hints import TimeHint, time_hints
from datamate.modules.understanding.normalize.understanding import Understanding, understand

__all__ = [
    "EntityHit",
    "EntityIndex",
    "TimeHint",
    "Understanding",
    "normalize_question",
    "time_hints",
    "understand",
]
