"""Gợi ý vai trò cột cho LLM (vd. "mã đơn", "số lượng quy về đơn vị cơ bản", "giá vốn").

Chỉ là GỢI Ý ghi thêm vào mô tả bảng: không đổi tên cột, không đụng dữ liệu. Nguyên tắc:
- chỉ ghi khi chắc: tên cột mơ hồ hoặc lạ thì bỏ trống, không đoán;
- phân tích theo cụm danh từ (từ đầu là từ chính, sau là từ bổ nghĩa), có ghép cụm từ trước;
- tên có dấu chỉ so với luật có dấu, để "hàng" / "hãng" / "hạng", "tiền" / "tiến" không lẫn;
- kiểm tra kiểu giá trị (ngày / số / chữ) và ngữ cảnh bảng trước khi ghi.
Luật nằm ở assets/lexicon/column_roles.tsv, cụm từ ghép ở column_compounds.txt.
"""

from __future__ import annotations

import functools
import re
import unicodedata
from dataclasses import dataclass
from pathlib import Path

import pandas as pd

from datamate.core.text import fold
from datamate.modules.domain.business_rules import classify_status

LEXICON_DIR = Path(__file__).resolve().parents[3] / "assets" / "lexicon"
_NO_HINT = "-"
# Khoá trong ``DataFrame.attrs``: vai trò do LLM đề xuất và đã được kiểm chứng (xem propose.py).
ROLES_KEY = "column_roles_override"

# Hai kiểu bỏ dấu thanh ("hoá" / "hóa", "thuỷ" / "thủy") đưa về một dạng.
_OLD_STYLE = {
    "oá": "óa",
    "oà": "òa",
    "oả": "ỏa",
    "oã": "õa",
    "oạ": "ọa",
    "oé": "óe",
    "oè": "òe",
    "oẻ": "ỏe",
    "oẽ": "õe",
    "oẹ": "ọe",
    "uý": "úy",
    "uỳ": "ùy",
    "uỷ": "ủy",
    "uỹ": "ũy",
    "uỵ": "ụy",
}


def _canonical(text: str) -> str:
    text = unicodedata.normalize("NFC", text).lower()
    for old, new in _OLD_STYLE.items():
        text = text.replace(old, new)
    return text


@dataclass(frozen=True)
class RoleRule:
    role: str
    kind: str  # date | number | text | any
    label: str
    heads: frozenset[str]  # rỗng = bất kỳ
    any_of: frozenset[str]
    none_of: frozenset[str]


@dataclass(frozen=True)
class ColumnRole:
    role: str
    label: str


def _words(cell: str) -> frozenset[str]:
    return frozenset(_canonical(w.strip()) for w in cell.split(",") if w.strip() and w != "*")


@functools.cache
def _compounds() -> tuple[str, ...]:
    lines = (LEXICON_DIR / "column_compounds.txt").read_text(encoding="utf-8").splitlines()
    phrases = {_canonical(x.strip()) for x in lines if x.strip() and not x.startswith("#")}
    return tuple(sorted(phrases, key=len, reverse=True))


@functools.cache
def rules() -> tuple[RoleRule, ...]:
    """Luật đọc từ column_roles.tsv, giữ nguyên thứ tự (luật đầu tiên khớp được dùng)."""
    out: list[RoleRule] = []
    for line in (LEXICON_DIR / "column_roles.tsv").read_text(encoding="utf-8").splitlines():
        if not line.strip() or line.startswith("#"):
            continue
        cells = [*line.split("\t"), "", "", "", "", ""][:6]
        role, kind, label, heads, any_of, none_of = (c.strip() for c in cells)
        out.append(RoleRule(role, kind, label, _words(heads), _words(any_of), _words(none_of)))
    return tuple(out)


def _split_camel(text: str) -> str:
    """'MaHoaDon' → 'Ma Hoa Don'; chỉ tách khi chữ hoa đứng ngay sau chữ thường."""
    out: list[str] = []
    for i, char in enumerate(text):
        after_lower = i and char.isupper() and text[i - 1].islower()
        # cuối cụm viết tắt hoa: "SLQuyDoi" → "SL Quy Doi"
        acronym_end = (
            0 < i < len(text) - 1
            and char.isupper()
            and text[i - 1].isupper()
            and text[i + 1].islower()
        )
        if after_lower or acronym_end:
            out.append(" ")
        out.append(char)
    return "".join(out)


def _tokens(column: str, *, folded: bool) -> list[str]:
    text = _canonical(_split_camel(str(column)))
    phrases = _compounds()
    if folded:
        text, phrases = fold(text), tuple(fold(p) for p in phrases)
    text = " " + " ".join(re.findall(r"\w+", text)) + " "
    text = text.replace("_", " ")
    for phrase in phrases:
        text = text.replace(f" {phrase} ", f" {phrase.replace(' ', '')} ")
    return text.split()


def _is_unaccented(column: str) -> bool:
    letters = [c for c in str(column) if c.isalpha()]
    return all(c.isascii() for c in letters)


def classify(column: str) -> RoleRule | None:
    """Luật đầu tiên khớp với tên cột; None nếu không luật nào khớp."""
    folded = _is_unaccented(column)
    tokens = _tokens(column, folded=folded)
    if not tokens:
        return None
    present = set(tokens)

    def norm(words: frozenset[str]) -> frozenset[str]:
        return frozenset(fold(w) for w in words) if folded else words

    for rule in rules():
        heads, any_of, none_of = norm(rule.heads), norm(rule.any_of), norm(rule.none_of)
        if heads and tokens[0] not in heads:
            continue
        if any_of and not present & any_of:
            continue
        if present & none_of:
            continue
        return rule
    return None


def _kind_ok(kind: str, series: pd.Series) -> bool:
    if kind == "date":
        return bool(pd.api.types.is_datetime64_any_dtype(series))
    if kind == "number":
        return bool(pd.api.types.is_numeric_dtype(series)) and not pd.api.types.is_bool_dtype(
            series
        )
    if kind == "text":
        return not pd.api.types.is_numeric_dtype(
            series
        ) and not pd.api.types.is_datetime64_any_dtype(series)
    return True


_IMPORT_ROLES = {"qty_imported", "import_price", "import_date", "import_amount"}
_IMPORT_CONTEXT = {
    "order_id": ("import_id", "mã phiếu nhập hàng"),
    "unit_price": ("import_price", "giá nhập"),
    "qty": ("qty_imported", "số lượng nhập"),
    "line_amount": ("import_amount", "tiền nhập hàng"),
    "event_date": ("import_date", "ngày nhập hàng"),
}


def _amount_matches(table: pd.DataFrame, qty: str, price: str, amount: str) -> bool:
    """Thành tiền ≈ số lượng × đơn giá ở phần lớn các dòng (cho phép lệch do giảm giá dòng)."""
    frame = table[[qty, price, amount]].dropna()
    if len(frame) < 20:
        return False
    expected = frame[qty] * frame[price]
    close = (expected - frame[amount]).abs() <= (frame[amount].abs() * 0.01).clip(lower=1)
    return bool(close.mean() >= 0.6)


_MAX_STATUS_VALUES = 15


def _looks_like_status(series: pd.Series) -> bool:
    """Cột chữ ít giá trị mà phần lớn dòng là trạng thái đơn quen (hoàn thành, huỷ, trả…)."""
    if pd.api.types.is_numeric_dtype(series) or pd.api.types.is_datetime64_any_dtype(series):
        return False
    counts = series.dropna().astype(str).value_counts()
    if counts.empty or len(counts) > _MAX_STATUS_VALUES:
        return False
    labels = {value: classify_status(value) for value in counts.index}
    known = sum(n for value, n in counts.items() if labels[value] != "khac")
    return known / counts.sum() >= 0.8 and len(set(labels.values()) - {"khac"}) >= 1 and (
        "hoan_thanh" in labels.values()
    )


def _product_by_values(table: pd.DataFrame, taken: set[str]) -> str | None:
    """Cột chữ chưa có vai trò, có nhiều tên khác nhau nhưng mỗi tên lặp lại nhiều lần."""
    best: tuple[int, str] | None = None
    for column in table.columns:
        series = table[column]
        if str(column) in taken or str(column).startswith("_") or not _kind_ok("text", series):
            continue
        values = series.dropna().astype(str)
        distinct = values.nunique()
        if len(values) < 0.9 * len(table) or not _MAX_STATUS_VALUES < distinct <= len(values) / 5:
            continue
        # Ít tên khác nhau nhất: danh mục hàng thường nhỏ hơn danh sách khách / ghi chú.
        if best is None or distinct < best[0]:
            best = (distinct, str(column))
    return best[1] if best else None


def _infer_by_values(table: pd.DataFrame, hints: dict[str, ColumnRole]) -> dict[str, ColumnRole]:
    """Vai trò suy từ GIÁ TRỊ khi tên cột không có trong từ điển (doanh nghiệp mới, tên lạ)."""
    found: dict[str, ColumnRole] = {}
    roles = {hint.role for hint in hints.values()}
    # Bảng bán hàng (có mã đơn, hoặc sổ bán có ngày + tiền) nhưng tên cột trạng thái lạ.
    is_sales = "order_id" in roles or {"event_date", "line_amount"} <= roles
    if is_sales and "status" not in roles:
        for column in table.columns:
            if column not in hints and _looks_like_status(table[column]):
                found[str(column)] = ColumnRole("status", "trạng thái đơn (suy từ giá trị cột)")
                break
    by_role = {hint.role: column for column, hint in hints.items()}
    if {"qty", "line_amount"} <= by_role.keys() and "product" not in roles:
        product = _product_by_values(table, {*hints, *found})
        if product is not None:
            found[product] = ColumnRole("product", "tên hàng (suy: cột chữ nhiều giá trị lặp lại)")
    if {"qty", "unit_price"} <= by_role.keys() and "line_amount" not in roles:
        for column in table.columns:
            if column in hints or not pd.api.types.is_numeric_dtype(table[column]):
                continue
            if _amount_matches(table, by_role["qty"], by_role["unit_price"], str(column)):
                found[str(column)] = ColumnRole(
                    "line_amount", "thành tiền của dòng hàng (suy: ≈ số lượng × đơn giá)"
                )
                break
    return found


def column_roles(table: pd.DataFrame) -> dict[str, ColumnRole]:
    """Gợi ý vai trò cho các cột của một bảng (chỉ những cột chắc chắn)."""
    found: dict[str, RoleRule] = {}
    for column in table.columns:
        rule = classify(str(column))
        if rule is None or rule.role == _NO_HINT or not _kind_ok(rule.kind, table[column]):
            continue
        found[str(column)] = rule

    roles = {rule.role for rule in found.values()}
    is_import_table = bool(roles & (_IMPORT_ROLES | {"import_id"}))
    hints: dict[str, ColumnRole] = {}
    for column, rule in found.items():
        role, label = rule.role, rule.label
        if role == "status" and "order_id" not in roles:
            continue  # trạng thái của bảng khách / nhà cung cấp… không phải trạng thái đơn
        if is_import_table:  # bảng nhập hàng: cột chung chung mang nghĩa "nhập"
            role, label = _IMPORT_CONTEXT.get(role, (role, label))
        hints[column] = ColumnRole(role, label)

    for column, role in table.attrs.get(ROLES_KEY, {}).items():
        if column in table.columns:
            hints[column] = ColumnRole(role, f"{role} (LLM nhận diện, đã kiểm chứng giá trị)")
    hints.update(_infer_by_values(table, hints))
    by_role = {hint.role: column for column, hint in hints.items()}
    if {"qty", "unit_price", "line_amount"} <= by_role.keys():
        amount = by_role["line_amount"]
        if _amount_matches(table, by_role["qty"], by_role["unit_price"], amount):
            hints[amount] = ColumnRole(
                "line_amount", hints[amount].label + " (≈ số lượng × đơn giá)"
            )
    return hints
