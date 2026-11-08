"""Vai trò cột do LLM đề xuất cho những cột mà luật tên cột không nhận ra, KIỂM CHỨNG bằng giá trị.

Luật tên cột (``roles.py``) chắc nhưng chỉ biết những tên đã thấy. Tên lạ ("Ngày TT", "So tien",
"Ghi chú" chứa trạng thái) làm bảng chuẩn tắc thiếu cột quan trọng. Ở đây LLM được xem tên cột
cùng vài giá trị mẫu và đề xuất vai trò; mỗi đề xuất phải qua kiểm chứng bằng giá trị (ngày đọc
được, tiền là số, mã đơn khớp bảng khác, trạng thái là từ trạng thái quen...) mới được dùng.
LLM chỉ đề xuất, code quyết định.

Module này thuần dữ liệu (không gọi LLM): lời gọi nằm ở tầng app, xem ``BusinessRegistry``.
"""

from __future__ import annotations

import json
import re
from dataclasses import dataclass, field
from typing import Any

import pandas as pd

from datamate.core.text import fold
from datamate.modules.data.ingestion import SOURCE_COLUMN
from datamate.modules.data.semantic.roles import ROLES_KEY, column_roles, rules
from datamate.modules.domain.business_rules import classify_status

# Khoá trong ``DataFrame.attrs`` lưu quy ước ô trống của cột trạng thái (vd. trống = hoàn thành).
BLANK_KEY = "status_blank"

DATE_ROLES = frozenset(
    {"event_date", "receipt_date", "import_date", "return_date", "delivery_date", "due_date",
     "effective_date", "expiry_date", "created_at", "birth_date"}
)
NUMBER_ROLES = frozenset(
    {"line_amount", "receipt_amount", "paid_amount", "order_total", "order_subtotal", "debt",
     "discount", "qty", "qty_base", "qty_delivered", "qty_imported", "qty_returned", "unit_price",
     "cost_price", "import_price", "import_amount", "refund", "list_price", "price_new",
     "price_old", "points"}
)
ID_ROLES = frozenset(
    {"order_id", "receipt_id", "return_id", "import_id", "product_code", "customer_code",
     "supplier_code", "staff_code", "lot_id"}
)
TEXT_ROLES = frozenset(
    {"product", "customer", "customer_group", "payment", "staff", "unit", "category", "status",
     "active_ingredient", "prescription"}
)
ALL_ROLES = DATE_ROLES | NUMBER_ROLES | ID_ROLES | TEXT_ROLES
# Chỉ những vai trò mà bảng chuẩn tắc và mô tả thật sự dùng, và code kiểm chứng được. Vai trò hiếm
# (hoạt chất, điểm, hạn dùng...) vẫn do luật tên cột nhận; để LLM đoán chỉ thêm nhãn sai.
PROPOSABLE = frozenset(
    {"order_id", "event_date", "created_at", "receipt_date", "status", "line_amount",
     "receipt_amount", "paid_amount", "order_total", "order_subtotal", "debt", "discount", "qty",
     "qty_base", "unit_price", "cost_price", "import_price", "import_amount", "qty_imported",
     "import_date", "import_id", "return_id", "return_date", "product", "product_code",
     "customer", "customer_code", "customer_group", "payment", "staff", "staff_code", "unit",
     "category", "supplier_code", "receipt_id"}
)
_PAYMENT_WORDS = (
    "tien mat", "chuyen khoan", "cash", "transfer", "cod", "vi dien tu", "ewallet", "ghi no",
    "debt", "the ", "card", "momo", "zalopay", "qr", "pos", "thu ho",
)
BLANK_LABELS = frozenset({"hoan_thanh", "huy", "tra_hang", "dang_giao"})
_MAX_COLUMNS = 80
_MIN_SHARE = 0.95
_JSON = re.compile(r"\{.*\}", re.DOTALL)


def role_vocabulary() -> dict[str, str]:
    """Mã vai trò → lời mô tả (lấy từ luật tên cột, giữ mô tả của luật đầu tiên)."""
    out: dict[str, str] = {}
    for rule in rules():
        if rule.role in PROPOSABLE and rule.role not in out:
            out[rule.role] = rule.label
    return {role: out.get(role, role) for role in sorted(PROPOSABLE)}


@dataclass(frozen=True)
class Proposal:
    role: str
    blank_is: str | None = None  # chỉ cho cột trạng thái: ô trống nghĩa là nhãn này


@dataclass
class Accepted:
    """Đề xuất đã qua kiểm chứng (theo bảng, theo cột) và lý do các đề xuất bị loại."""

    roles: dict[str, dict[str, Proposal]] = field(default_factory=dict)
    rejected: list[str] = field(default_factory=list)
    reply: str = ""  # câu trả lời gốc của LLM (để chẩn đoán)

    def to_json(self) -> dict[str, Any]:
        return {
            "roles": {
                t: {c: {"role": p.role, "blank_is": p.blank_is} for c, p in cols.items()}
                for t, cols in self.roles.items()
            },
            "rejected": self.rejected,
            "reply": self.reply[:4000],
        }

    @classmethod
    def from_json(cls, data: dict[str, Any]) -> Accepted:
        roles = {
            t: {c: Proposal(v["role"], v.get("blank_is")) for c, v in cols.items()}
            for t, cols in data.get("roles", {}).items()
        }
        return cls(roles, list(data.get("rejected", [])), str(data.get("reply", "")))


def _unresolved(table: pd.DataFrame) -> list[str]:
    known = column_roles(table)
    return [str(c) for c in table.columns if c != SOURCE_COLUMN and str(c) not in known]


def _samples(series: pd.Series) -> str:
    present = series.dropna()
    if present.empty:
        return "(rỗng)"
    counts = present.astype(str).value_counts()
    values = counts.index[:6] if len(counts) <= 12 else present.astype(str).unique()[:4]
    return " | ".join(str(v)[:30] for v in values)


def render_tables(tables: dict[str, pd.DataFrame]) -> str:
    """Mô tả gọn các bảng có cột chưa rõ vai trò; chuỗi rỗng nếu không còn gì cần hỏi."""
    parts: list[str] = []
    budget = _MAX_COLUMNS
    for name, table in tables.items():
        columns = _unresolved(table)[:budget]
        if not columns or len(table) < 5:
            continue
        budget -= len(columns)
        # chỉ nêu các VAI TRÒ đã có (không kèm tên cột) để LLM không chép lại các cột đã rõ
        known = ", ".join(sorted({h.role for h in column_roles(table).values()})) or "(chưa có)"
        lines = [f'## Bảng "{name}" ({len(table)} dòng)', f"Vai trò đã có trong bảng: {known}"]
        for column in columns:
            series = table[column]
            kind = (
                "ngày" if pd.api.types.is_datetime64_any_dtype(series)
                else "số" if pd.api.types.is_numeric_dtype(series)
                else "chữ"
            )
            lines.append(
                f'- "{column}": {kind}, {series.nunique()} giá trị khác nhau, '
                f"trống {series.isna().mean():.0%}, ví dụ: {_samples(series)}"
            )
        parts.append("\n".join(lines))
        if budget <= 0:
            break
    return "\n\n".join(parts)


_OBJECT = re.compile(r"\{[^{}]*\}")


def _table_key(name: object) -> str:
    """Tên bảng bỏ đuôi file và số kỳ cuối ("a_1.xlsx" ~ "a"): LLM hay chép tên file từ README."""
    base = re.sub(r"\.(xlsx|csv|sqlite)$", "", str(name), flags=re.IGNORECASE)
    return re.sub(r"[_\- ]*\d+$", "", base).lower()


def _resolve_table(name: object, tables: dict[str, pd.DataFrame]) -> str | None:
    if isinstance(name, str) and name in tables:
        return name
    hits = [t for t in tables if _table_key(t) == _table_key(name)]
    return hits[0] if len(hits) == 1 else None


def parse_proposals(text: str, tables: dict[str, pd.DataFrame]) -> dict[str, dict[str, Proposal]]:
    """Đọc mọi đối tượng JSON {"table", "column", "role", "blank_is"} trong câu trả lời.

    Mỗi đối tượng đọc độc lập (một dòng hay nhiều dòng đều được) nên đầu ra bị cắt giữa chừng chỉ
    mất đối tượng cuối. Bỏ bảng, cột, vai trò lạ.
    """
    out: dict[str, dict[str, Proposal]] = {}
    for match in _OBJECT.finditer(text):
        try:
            item = json.loads(match.group(0))
        except json.JSONDecodeError:
            continue
        name = _resolve_table(item.get("table"), tables)
        column, role = item.get("column"), item.get("role")
        if name is None or column not in tables[name].columns or role not in PROPOSABLE:
            continue
        blank = item.get("blank_is")
        out.setdefault(name, {})[column] = Proposal(role, blank if blank in BLANK_LABELS else None)
    return out


def _share(mask: pd.Series) -> float:
    return float(mask.mean()) if len(mask) else 0.0


def _converted(series: pd.Series, role: str) -> tuple[pd.Series | None, str | None]:
    """(cột đã đổi kiểu, None) nếu đủ giá trị đọc được theo vai trò, không thì (None, lý do)."""
    present = series.dropna()
    if present.empty:
        return None, "cột rỗng"
    if role in DATE_ROLES:
        if pd.api.types.is_numeric_dtype(series):  # số nguyên không phải ngày (tránh năm 1970)
            return None, "cột số, không phải ngày"
        parsed = (
            series
            if pd.api.types.is_datetime64_any_dtype(series)
            else pd.to_datetime(series, errors="coerce", format="mixed")
        )
        ok = _share(parsed.loc[present.index].notna())
        return (parsed, None) if ok >= _MIN_SHARE else (None, f"chỉ {ok:.0%} đọc được thành ngày")
    if role in NUMBER_ROLES:
        if pd.api.types.is_bool_dtype(series):
            return None, "cột đúng/sai, không phải số"
        parsed = (
            series
            if pd.api.types.is_numeric_dtype(series)
            else pd.to_numeric(series, errors="coerce")
        )
        ok = _share(parsed.loc[present.index].notna())
        return (parsed, None) if ok >= _MIN_SHARE else (None, f"chỉ {ok:.0%} đọc được thành số")
    return series, None


def _looks_like_ids(keys: pd.Series) -> bool:
    """Giống mã chứng từ: cùng một khuôn chữ/số, nhiều giá trị khác nhau, không có dấu cách."""
    if keys.nunique() < max(5, 0.05 * len(keys)):
        return False
    shapes = keys.str.replace(r"[A-Za-z]", "a", regex=True).str.replace(r"\d", "9", regex=True)
    dominant = shapes.value_counts(normalize=True).iloc[0]
    return bool(dominant >= 0.9 and not keys.str.contains(" ").any())


def _known_order_ids(tables: dict[str, pd.DataFrame]) -> set[str]:
    ids: set[str] = set()
    for table in tables.values():
        for column, hint in column_roles(table).items():
            if hint.role == "order_id":
                ids.update(table[column].dropna().astype(str).str.strip())
    return ids


def verify(  # noqa: PLR0911, PLR0912
    table: pd.DataFrame, column: str, proposal: Proposal, tables: dict[str, pd.DataFrame]
) -> tuple[pd.Series | None, str | None]:
    """Kiểm chứng một đề xuất bằng giá trị. Trả (cột đã chuẩn hoá, None) hoặc (None, lý do loại)."""
    role = proposal.role
    if role in {r.role for r in column_roles(table).values()}:
        return None, f"bảng đã có cột vai trò {role}"
    series, problem = _converted(table[column], role)
    if series is None:
        return None, problem
    present = series.dropna()
    if role in ID_ROLES | TEXT_ROLES and pd.api.types.is_datetime64_any_dtype(series):
        return None, "cột ngày không thể mang vai trò chữ / mã"
    if role == "order_id":
        known = _known_order_ids(tables)
        keys = present.astype(str).str.strip()
        if known and _share(keys.isin(known)) < 0.5:
            return None, "giá trị không khớp mã đơn của các bảng khác"
        if not known and not _looks_like_ids(keys):
            return None, "không có bảng đơn để đối chiếu và giá trị không giống mã đơn"
    elif role == "status":
        labels = present.astype(str).map(classify_status)
        if _share(labels != "khac") < 0.8 or present.nunique() > 20:
            return None, "giá trị không phải các cách ghi trạng thái đơn quen"
        if proposal.blank_is is None and "hoan_thanh" not in set(labels):
            return None, "không có trạng thái hoàn thành và không nói ô trống nghĩa là gì"
    elif role == "payment":
        folded = present.astype(str).map(fold).drop_duplicates()
        hits = folded.map(lambda v: any(w in f" {v} " for w in _PAYMENT_WORDS))
        if present.nunique() > 12 or _share(hits) < 0.5:
            return None, "giá trị không phải hình thức thanh toán quen (tiền mặt, chuyển khoản…)"
    elif role == "product":
        if present.nunique() < 3 or present.nunique() > 0.5 * len(present):
            return None, "số tên hàng khác nhau không hợp lý"
    elif role in {"line_amount", "receipt_amount", "paid_amount", "order_total", "order_subtotal"}:
        if present.nunique() < 2 or _share(present >= 0) < 0.9:
            return None, "số tiền hằng số hoặc âm quá nhiều"
    elif role in ID_ROLES and present.nunique() < 2:
        return None, "mã chỉ có một giá trị"
    return series, None


def accept(tables: dict[str, pd.DataFrame], proposals: dict[str, dict[str, Proposal]]) -> Accepted:
    """Giữ các đề xuất qua kiểm chứng; mỗi vai trò chỉ gán cho một cột trong một bảng."""
    result = Accepted()
    for name, columns in proposals.items():
        used: set[str] = set()
        resolved = column_roles(tables[name])
        for column, proposal in columns.items():
            if column in resolved:  # cột đã có vai trò theo tên: LLM không được ghi đè
                result.rejected.append(f"{name}.{column}: đã có vai trò {resolved[column].role}")
                continue
            if proposal.role in used:
                msg = f"{name}.{column}: vai trò {proposal.role} đã gán cho cột khác"
                result.rejected.append(msg)
                continue
            series, problem = verify(tables[name], column, proposal, tables)
            if series is None:
                result.rejected.append(f"{name}.{column} ({proposal.role}): {problem}")
                continue
            used.add(proposal.role)
            result.roles.setdefault(name, {})[column] = proposal
    return result


def apply_roles(
    tables: dict[str, pd.DataFrame], accepted: Accepted
) -> dict[str, pd.DataFrame]:
    """Bản sao các bảng được đổi (đổi kiểu cột, ghi vai trò vào ``attrs``); bảng khác giữ nguyên."""
    out = dict(tables)
    for name, columns in accepted.roles.items():
        table = out[name].copy(deep=False)
        roles: dict[str, str] = dict(table.attrs.get(ROLES_KEY, {}))
        for column, proposal in columns.items():
            series, _ = _converted(table[column], proposal.role)
            if series is not None:
                table[column] = series
            roles[column] = proposal.role
            if proposal.role == "status" and proposal.blank_is:
                table.attrs[BLANK_KEY] = {column: proposal.blank_is}
        table.attrs[ROLES_KEY] = roles
        out[name] = table
    return out
