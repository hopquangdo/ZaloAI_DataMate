"""Dựng bảng chuẩn tắc (cùng cột, cùng nghĩa mọi doanh nghiệp) từ vai trò cột và đặc tả rulebook.

Mỗi doanh nghiệp bố trí bảng một kiểu: một bảng phẳng, tách bảng đơn và bảng chi tiết, chỉ có sổ
bán hàng không có mã đơn, hoặc chỉ có bảng đơn không có dòng hàng. Bộ dựng chọn bảng theo VAI TRÒ
CỘT, không theo tên bảng, rồi tạo:

- ``don_chuan``: mỗi đơn một dòng (mã đơn, ngày đặt, trạng thái chuẩn, có tính doanh thu không,
  doanh thu đơn, khách, nhóm khách, hình thức thanh toán, nhân viên);
- ``dong_hang_chuan``: mỗi dòng hàng một dòng (kèm ngày, trạng thái, cờ tính doanh thu của đơn).

Bảng chuẩn mang theo MỌI cột khác của bảng gốc (kênh bán, ca, ghi chú…) dưới tên gốc, nên bảng
gốc đã dùng (``Canonical.replaces``) được thay hẳn: bộ giải không thể lỡ đọc bảng gốc mà bỏ qua
trạng thái hay dòng lặp. Không dựng được thì trả về rỗng (bộ giải dùng bảng gốc như cũ).
Dòng lặp: hai dòng của CÙNG MỘT đơn giống nhau ở mọi ô là lỗi xuất file, tính một lần (rulebook §8);
bảng không ghi theo đơn thì mỗi dòng là một lần ghi, giữ nguyên.
"""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass

import pandas as pd

from datamate.core.text import fold, normalize_text
from datamate.modules.data.ingestion import SOURCE_COLUMN
from datamate.modules.data.semantic import column_roles
from datamate.modules.data.semantic.propose import BLANK_KEY
from datamate.modules.domain.business_rules import (
    DEFAULT_SPEC,
    RuleSpec,
    classify_status,
    is_debt_payment,
    is_walk_in,
)

ORDERS = "don_chuan"
LINES = "dong_hang_chuan"
PAYMENTS = "thanh_toan_chuan"
IMPORTS = "nhap_hang_chuan"
# Bản đã lọc sẵn cờ "Tính vào doanh thu": dùng cho đếm đơn, doanh thu, số lượng, lãi gộp.
VIEW_ORDERS = "don_tinh_doanh_thu"
VIEW_LINES = "dong_hang_tinh_doanh_thu"

C_ORDER, C_DATE, C_STATUS = "Mã đơn", "Ngày đặt", "Trạng thái chuẩn"
C_COUNTS, C_REVENUE, C_NLINES = "Tính vào doanh thu", "Doanh thu đơn", "Số dòng"
C_CUSTOMER, C_CUSTOMER_CODE, C_GROUP = "Khách", "Mã khách", "Nhóm khách"
C_PAYMENT, C_STAFF = "Hình thức thanh toán", "Nhân viên"
C_PRODUCT, C_QTY, C_QTY_BASE = "Tên hàng", "Số lượng", "Số lượng quy đổi"
C_AMOUNT, C_PRICE = "Thành tiền dòng", "Đơn giá"
C_TOTAL, C_DEBT_ORDER = "Tổng đơn", "Đơn ghi nợ"
C_PAID_SAME_DAY, C_NEW_DEBT = "Đã trả trong ngày mua", "Nợ thêm"
C_PAID_ON, C_PAID, C_PAY_METHOD = "Ngày thu", "Số tiền thu", "Hình thức thu"
C_AFTER, C_REPAY = "Trả sau ngày mua", "Là trả nợ"
C_COST, C_PROFIT = "Giá vốn", "Lãi gộp dòng"
C_PRODUCT_CODE = "Mã hàng"
C_TIME, C_SHIFT = "Giờ đặt", "Ca"
C_CLIENT_ID, C_CLIENT_NAME = "Khách định danh", "Tên khách"
C_STAFF_CODE = "Mã nhân viên"
C_IMPORT_ID, C_IMPORT_DATE, C_IMPORT_STATUS = "Mã phiếu nhập", "Ngày nhập", "Trạng thái phiếu"
C_IMPORT_QTY, C_IMPORT_UNIT = "Số lượng nhập", "Đơn vị nhập"
C_IMPORT_PRICE, C_IMPORT_AMOUNT = "Giá nhập", "Thành tiền nhập"
_MAX_CATALOG_ATTRS = 10

_ATTRIBUTES = (
    (C_CUSTOMER, "customer"),
    (C_CUSTOMER_CODE, "customer_code"),
    (C_PAYMENT, "payment"),
    (C_STAFF, "staff"),
    (C_STAFF_CODE, "staff_code"),
)
_LINE_FIELDS = (
    (C_PRODUCT, "product"),
    (C_QTY, "qty"),
    (C_QTY_BASE, "qty_base"),
    (C_AMOUNT, "line_amount"),
    (C_PRICE, "unit_price"),
    (C_COST, "cost_price"),
)
_LINE_ORDER = [
    C_ORDER, C_DATE, C_STATUS, C_COUNTS, C_PRODUCT, C_QTY, C_QTY_BASE, C_AMOUNT, C_PRICE, C_COST,
    C_PROFIT, C_PRODUCT_CODE,
]
_ORDER_COLUMNS = [C_ORDER, C_DATE, C_STATUS, C_COUNTS, C_REVENUE, C_NLINES, C_GROUP] + [
    name for name, _ in _ATTRIBUTES
]
_ID_OVERLAP = 0.9


def _renames(sources: list[_Source]) -> tuple[tuple[str, str], ...]:
    """Cột gốc nào đã đổi tên khi vào bảng chuẩn (README vẫn gọi bằng tên gốc)."""
    pairs: dict[str, str] = {}
    fields = (
        (C_ORDER, "order_id"), (C_STATUS, "status"), (C_CUSTOMER_CODE, "customer_code"),
        (C_PRODUCT_CODE, "product_code"), *_LINE_FIELDS, *_ATTRIBUTES,
    )
    for src in sources:
        for canonical, role in fields:
            raw = _code_col(src) if role == "product_code" else src.col(role)
            if raw and str(raw) != canonical and raw not in pairs:
                pairs[str(raw)] = canonical
        if src.date and src.date != C_DATE:
            pairs.setdefault(str(src.date), C_DATE)
    return tuple(sorted(pairs.items()))


def _with_views(tables: dict[str, pd.DataFrame]) -> dict[str, pd.DataFrame]:
    """Thêm bản đã lọc cờ doanh thu của bảng đơn / bảng dòng hàng (quên lọc cờ không còn xảy ra)."""
    out = dict(tables)
    for source, view in ((ORDERS, VIEW_ORDERS), (LINES, VIEW_LINES)):
        if source in tables:
            out[view] = tables[source][tables[source][C_COUNTS].astype(bool)].reset_index(drop=True)
    return out


def _order_time(head: _Source) -> pd.Series | None:
    """Cột giờ đặt đơn: cột ngày của đơn nếu có giờ, nếu không thì cột "thời điểm tạo"."""
    for column in [head.date, *head.roles.get("created_at", [])]:
        if column is None or not pd.api.types.is_datetime64_any_dtype(head.table[column]):
            continue
        present = head.table[column].dropna()
        if len(present) and (present.dt.normalize() != present).any():
            return head.table[column]
    return None


def _add_shift(orders: pd.DataFrame, head: _Source, spec: RuleSpec) -> bool:
    """Thêm "Giờ đặt" và "Ca" (theo giờ tạo đơn, mốc ca lấy từ ``spec``); False nếu không có giờ."""
    times = _order_time(head)
    if times is None:
        return False
    keyed = head.table.assign(_k=_key(head.table[head.col("order_id")]), _t=times)
    by_id = keyed.drop_duplicates("_k").set_index("_k")["_t"]
    orders[C_TIME] = orders[C_ORDER].map(by_id)

    def label(moment: pd.Timestamp) -> object:
        if pd.isna(moment):
            return pd.NA
        return next((n for n, a, b in spec.shifts if a <= moment.hour < b), "ngoài ca")

    orders[C_SHIFT] = orders[C_TIME].map(label)
    return True


@dataclass(frozen=True)
class Canonical:
    """Các bảng chuẩn tắc dựng được và ghi chú về nguồn gốc (để mô tả cho LLM và để gỡ lỗi)."""

    tables: dict[str, pd.DataFrame]
    notes: tuple[str, ...] = ()
    replaces: tuple[str, ...] = ()  # bảng gốc đã nằm trọn trong bảng chuẩn
    renames: tuple[tuple[str, str], ...] = ()  # (tên cột gốc trong README, tên cột chuẩn)


@dataclass(frozen=True)
class _Source:
    """Một bảng gốc cùng vai trò các cột đã biết."""

    name: str
    table: pd.DataFrame
    roles: dict[str, list[str]]

    def col(self, role: str) -> str | None:
        columns = self.roles.get(role)
        return columns[0] if columns else None

    @property
    def date(self) -> str | None:
        """Cột ngày của đơn: kiểu ngày, nhiều ngày khác nhau nhất (loại cột chỉ có giờ)."""
        best, best_score = None, 0
        for column in self.roles.get("event_date", []):
            if not pd.api.types.is_datetime64_any_dtype(self.table[column]):
                continue
            score = self.table[column].dropna().dt.normalize().nunique()
            if score > best_score:
                best, best_score = column, score
        return best

    def has_item(self) -> bool:
        return any(self.col(r) for r in ("product", "qty", "qty_base"))


def _sources(tables: dict[str, pd.DataFrame]) -> list[_Source]:
    result = []
    for name, table in tables.items():
        by_role: dict[str, list[str]] = {}
        for column, hint in column_roles(table).items():
            by_role.setdefault(hint.role, []).append(column)
        result.append(_Source(name, table, by_role))
    return result


def _key(series: pd.Series) -> pd.Series:
    return series.astype("string").str.strip()


def _infer_order_ids(sources: list[_Source]) -> None:
    """Bảng chưa có cột mã đơn: tìm cột chữ mà đa số giá trị là mã đơn của bảng đơn khác."""
    known: set[str] = set()
    for src in sources:
        column = src.col("order_id")
        if column and src.table[column].nunique() >= 0.9 * max(len(src.table), 1):
            known.update(_key(src.table[column]).dropna())
    if len(known) < 20:
        return
    for src in sources:
        if src.col("order_id"):
            continue
        for column in src.table.columns:
            series = src.table[column]
            if column == SOURCE_COLUMN or pd.api.types.is_numeric_dtype(series):
                continue
            if pd.api.types.is_datetime64_any_dtype(series):
                continue
            values = _key(series).dropna()
            if len(values) and values.isin(known).mean() >= _ID_OVERLAP:
                src.roles["order_id"] = [str(column)]
                break


def _is_lines(src: _Source) -> bool:
    return bool(src.col("order_id") and src.col("line_amount") and src.has_item())


def _is_sales_book(src: _Source) -> bool:
    """Sổ bán hàng không ghi theo đơn: có ngày, thành tiền, hàng nhưng không có mã đơn."""
    return bool(
        not src.col("order_id") and src.col("line_amount") and src.has_item() and src.date
    )


def _is_header(src: _Source) -> bool:
    has_value = any(src.col(r) for r in ("status", "order_subtotal", "order_total"))
    return bool(src.col("order_id") and src.date and has_value)


def _largest(sources: list[_Source]) -> _Source | None:
    return max(sources, key=lambda s: len(s.table), default=None)


def _returned_orders(sources: list[_Source]) -> set[str]:
    """Mã đơn có phiếu trả hàng (bảng trả hàng riêng: có mã phiếu trả và mã đơn)."""
    returned: set[str] = set()
    for src in sources:
        order_col = src.col("order_id")
        if src.col("return_id") and order_col:
            returned.update(_key(src.table[order_col]).dropna())
    return returned


def _group_by_customer_code(sources: list[_Source]) -> pd.Series | None:
    """Nhóm khách theo mã khách, lấy từ bảng khách (có mã khách và nhóm khách, không có mã đơn)."""
    for src in sources:
        code, group = src.col("customer_code"), src.col("customer_group")
        if code and group and not src.col("order_id"):
            frame = src.table[[code, group]].dropna()
            frame = frame.assign(**{code: _key(frame[code])}).drop_duplicates(code)
            return frame.set_index(code)[group]
    return None


def _customer_names(sources: list[_Source]) -> pd.Series | None:
    """Tên khách theo mã khách, từ bảng khách (có mã khách và tên, không có mã đơn)."""
    for src in sources:
        code = src.col("customer_code")
        if not code or src.col("order_id") or len(src.table) > 20000:
            continue
        name = src.col("customer") or _name_col(src.table, {code})
        if name:
            frame = src.table[[code, name]].dropna()
            frame = frame.assign(**{code: _key(frame[code])}).drop_duplicates(code)
            return frame.set_index(code)[name]
    return None


def _add_customer_identity(orders: pd.DataFrame, sources: list[_Source]) -> None:
    """Rulebook §3: có mã khách thì mỗi mã là một khách; đơn không mã (khách lẻ) không phải khách.

    Không có mã khách thì xác định theo tên ghi trên đơn (hai tên chỉ khác cách viết là một khách),
    bỏ khách lẻ. Thêm "Khách định danh" (rỗng với khách lẻ) và "Tên khách" để trả lời "ai".
    """
    if C_CUSTOMER_CODE in orders and orders[C_CUSTOMER_CODE].notna().any():
        codes = _key(orders[C_CUSTOMER_CODE])
        names = _customer_names(sources)
        shown = codes.map(names) if names is not None else None
        fallback = orders.get(C_CUSTOMER, codes)
        orders[C_CLIENT_ID] = codes
        named = fallback if shown is None else shown.fillna(fallback)
        orders[C_CLIENT_NAME] = named.where(orders[C_CLIENT_ID].notna())
    elif C_CUSTOMER in orders:
        names = orders[C_CUSTOMER]
        real = names.notna() & ~names.map(is_walk_in).astype(bool)
        orders[C_CLIENT_ID] = names.map(
            lambda v: normalize_text(v) if isinstance(v, str) else None
        ).where(real)
        orders[C_CLIENT_NAME] = names.where(real)


def _add_staff_names(orders: pd.DataFrame, sources: list[_Source]) -> None:
    """Đơn chỉ có mã nhân viên: ghép tên từ bảng nhân viên (nếu có) để câu "ai" ra tên."""
    if C_STAFF in orders or C_STAFF_CODE not in orders:
        return
    names = None
    for src in sources:
        code = src.col("staff_code")
        if not code or src.col("order_id") or len(src.table) > 5000:
            continue
        table = src.table.assign(_k=_norm_key(src.table[code])).dropna(subset=["_k"])
        table = table.drop_duplicates("_k").set_index("_k")
        label = src.col("staff") or _name_col(table, {code})
        if label:
            names = table[label]
            break
    codes = _norm_key(orders[C_STAFF_CODE])
    shown = codes.map(names) if names is not None else codes
    orders[C_STAFF] = shown.fillna(orders[C_STAFF_CODE])


def _status_like_column(table: pd.DataFrame, skip: set[str]) -> str | None:
    """Cột chữ ít giá trị mà phần lớn là trạng thái quen (hoàn thành, huỷ…), dù tên cột không rõ."""
    for column in table.columns:
        series = table[column]
        if str(column) in skip or pd.api.types.is_numeric_dtype(series):
            continue
        if pd.api.types.is_datetime64_any_dtype(series):
            continue
        values = series.dropna().astype(str)
        if values.empty or values.nunique() > 12:
            continue
        known = values.map(classify_status) != "khac"
        if known.mean() >= 0.8:
            return str(column)
    return None


def _import_sources(
    sources: list[_Source], skip: set[str]
) -> tuple[_Source | None, _Source | None]:
    """(bảng dòng hàng nhập, bảng phiếu nhập có ngày) theo vai trò cột."""
    needed = ("import_id", "qty_imported", "import_price")
    lines = _largest([s for s in sources if s.name not in skip and all(s.col(r) for r in needed)])
    if lines is None:
        return None, None
    headers = [
        s
        for s in sources
        if s.name != lines.name and s.col("import_id") and not s.col("qty_imported")
        and s.roles.get("import_date")
    ]
    return lines, _largest(headers)


def _import_header_fields(
    frame: pd.DataFrame, header: _Source
) -> None:
    """Ngày nhập và trạng thái phiếu lấy từ bảng phiếu, ghép theo mã phiếu."""
    date_column = header.roles["import_date"][0]
    table = header.table.assign(_k=_key(header.table[header.col("import_id")]))
    table = table.drop_duplicates("_k").set_index("_k")
    frame[C_IMPORT_DATE] = frame[C_IMPORT_ID].map(table[date_column]).to_numpy()
    status = _status_like_column(table, {date_column})
    if status:
        mapped = frame[C_IMPORT_ID].map(table[status]).map(classify_status)
        frame[C_IMPORT_STATUS] = mapped.to_numpy()


def _imports(sources: list[_Source], skip: set[str]) -> tuple[pd.DataFrame | None, list[str]]:
    """Mỗi dòng một dòng hàng của phiếu nhập: ngày, trạng thái phiếu, hàng, số lượng, giá, tiền."""
    lines_src, header = _import_sources(sources, skip)
    if lines_src is None:
        return None, []
    table = lines_src.table
    ids = _key(table[lines_src.col("import_id")]).to_numpy()
    frame = pd.DataFrame({C_IMPORT_ID: ids}, index=table.index)
    own_date = lines_src.roles.get("import_date")
    if own_date:
        frame[C_IMPORT_DATE] = table[own_date[0]].to_numpy()
    elif header is not None:
        _import_header_fields(frame, header)
    else:
        return None, []
    if C_IMPORT_STATUS not in frame:
        frame[C_IMPORT_STATUS] = pd.NA
    product, code, unit = lines_src.col("product"), _code_col(lines_src), lines_src.col("unit")
    frame[C_PRODUCT] = table[product].to_numpy() if product else pd.NA
    frame[C_PRODUCT_CODE] = table[code].to_numpy() if code else pd.NA
    frame[C_IMPORT_QTY] = table[lines_src.col("qty_imported")].to_numpy()
    frame[C_IMPORT_UNIT] = table[unit].to_numpy() if unit else pd.NA
    frame[C_IMPORT_PRICE] = table[lines_src.col("import_price")].to_numpy()
    frame[C_IMPORT_AMOUNT] = frame[C_IMPORT_QTY] * frame[C_IMPORT_PRICE]
    used = {lines_src.name, *([header.name] if header else [])}
    notes = [f"phiếu nhập từ {', '.join(sorted(used))}"]
    notes.extend(_enrich_products(frame, lines_src, sources, used))
    return frame.reset_index(drop=True), notes


def _add_imports(
    tables: dict[str, pd.DataFrame], sources: list[_Source], skip: set[str]
) -> list[str]:
    imports, notes = _imports(sources, skip)
    if imports is not None:
        tables[IMPORTS] = imports
    return notes


def _status(src: _Source, labels: Mapping[str, str]) -> pd.Series | None:
    """Nhãn chuẩn của cột trạng thái: nhãn đã gán cho giá trị lạ, còn lại theo luật code."""
    column = src.col("status")
    if column is None:
        return None
    blank = src.table.attrs.get(BLANK_KEY, {}).get(column)  # vd. ô trống = đơn hoàn thành

    def label(value: object) -> str:
        if blank and pd.isna(value):
            return blank
        return labels.get(str(value)) or classify_status(value)

    return src.table[column].map(label)


def _counts_flag(
    status: pd.Series | None, ids: pd.Series, returned: set[str], spec: RuleSpec
) -> pd.Series:
    """Cờ "đơn tính vào doanh thu": trạng thái thuộc đặc tả và (nếu cần) đơn không có phiếu trả."""
    if status is None:
        counts = pd.Series(True, index=ids.index)
    else:
        counts = status.isin(spec.revenue_statuses)
    if spec.partial_return_voids_order and returned:
        counts &= ~ids.isin(returned)
    return counts


def _payment_source(
    sources: list[_Source], order_ids: set[str], skip: set[str]
) -> tuple[_Source, str, str, str] | None:
    """Bảng ghi từng lần khách trả tiền: mã đơn khớp đơn đã dựng, có ngày và số tiền, không hàng."""
    best: tuple[int, _Source, str, str, str] | None = None
    for src in sources:
        if src.name in skip or any(src.col(r) for r in ("product", "qty", "qty_base")):
            continue
        amount = src.col("receipt_amount") or src.col("line_amount")
        dates = [c for r in ("receipt_date", "event_date") for c in src.roles.get(r, [])]
        dates = [c for c in dates if pd.api.types.is_datetime64_any_dtype(src.table[c])]
        if not amount or not dates or src.table.empty:
            continue
        for column in src.roles.get("order_id", []):
            overlap = _key(src.table[column]).dropna().isin(order_ids).mean()
            if overlap >= _ID_OVERLAP and (best is None or len(src.table) > best[0]):
                best = (len(src.table), src, column, amount, dates[0])
    return best[1:] if best else None


def _add_payments(
    orders: pd.DataFrame, head: _Source, sources: list[_Source], skip: set[str]
) -> tuple[pd.DataFrame | None, str | None]:
    """Thêm cột công nợ vào ``orders`` (tại chỗ) và dựng bảng từng lần thu tiền (rulebook §4)."""
    found = _payment_source(sources, set(orders[C_ORDER].dropna()), skip)
    if found is None:
        return None, None
    src, order_col, amount_col, date_col = found
    table = src.table
    pay = pd.DataFrame(
        {
            C_ORDER: _key(table[order_col]).to_numpy(),
            C_PAID_ON: table[date_col].to_numpy(),
            C_PAID: table[amount_col].to_numpy(),
        }
    )
    method = src.col("payment")
    pay[C_PAY_METHOD] = table[method].to_numpy() if method else pd.NA

    if C_PAYMENT in orders:
        orders[C_DEBT_ORDER] = orders[C_PAYMENT].map(is_debt_payment).astype(bool)
    elif head.col("debt"):
        debt = head.table.assign(_k=_key(head.table[head.col("order_id")])).drop_duplicates("_k")
        orders[C_DEBT_ORDER] = orders[C_ORDER].map(debt.set_index("_k")[head.col("debt")]).gt(0)
    else:
        orders[C_DEBT_ORDER] = False
    total_col = head.col("order_total")
    if total_col:
        by_id = head.table.assign(_k=_key(head.table[head.col("order_id")])).drop_duplicates("_k")
        orders[C_TOTAL] = orders[C_ORDER].map(by_id.set_index("_k")[total_col])
        orders[C_TOTAL] = orders[C_TOTAL].fillna(orders[C_REVENUE])
    else:
        orders[C_TOTAL] = orders[C_REVENUE]

    by_order = orders.set_index(C_ORDER)
    pay[C_DATE] = pay[C_ORDER].map(by_order[C_DATE])
    pay[C_STATUS] = pay[C_ORDER].map(by_order[C_STATUS])
    pay[C_DEBT_ORDER] = pay[C_ORDER].map(by_order[C_DEBT_ORDER]).fillna(False).astype(bool)
    after = pay[C_PAID_ON].dt.normalize() > pay[C_DATE].dt.normalize()
    pay[C_AFTER] = after.fillna(False)
    pay[C_REPAY] = pay[C_DEBT_ORDER] & pay[C_AFTER] & (pay[C_STATUS] != "huy")
    same_day = pay[~pay[C_AFTER]].groupby(C_ORDER)[C_PAID].sum()
    orders[C_PAID_SAME_DAY] = orders[C_ORDER].map(same_day).fillna(0.0)
    owed = (orders[C_TOTAL] - orders[C_PAID_SAME_DAY]).clip(lower=0)
    orders[C_NEW_DEBT] = owed.where(orders[C_DEBT_ORDER] & (orders[C_STATUS] != "huy"), 0.0)
    for name in (C_CLIENT_ID, C_CLIENT_NAME):  # để tính dư nợ theo khách
        if name in orders:
            pay[name] = pay[C_ORDER].map(by_order[name])
    columns = [C_ORDER, C_PAID_ON, C_PAID, C_PAY_METHOD, C_DATE, C_STATUS, C_DEBT_ORDER, C_AFTER]
    columns += [c for c in (C_CLIENT_ID, C_CLIENT_NAME) if c in pay]
    return pay[[*columns, C_REPAY]].reset_index(drop=True), src.name


def _code_col(src: _Source) -> str | None:
    """Cột mã hàng của bảng: trong các cột cùng vai trò, lấy cột có nhiều giá trị khác nhau nhất
    (loại cột mã cửa hàng / chi nhánh chỉ có một vài giá trị)."""
    columns = src.roles.get("product_code", [])
    return max(columns, key=lambda c: src.table[c].nunique(), default=None)


def _name_col(table: pd.DataFrame, taken: set[str]) -> str | None:
    """Cột tên hàng của bảng danh mục: chữ gần như không trùng, phần lớn có dấu cách, không phải
    đường dẫn hay mã."""
    best: tuple[float, str] | None = None
    for column in table.columns:
        series = table[column]
        if str(column) in taken or str(column).startswith("_") or not _kind_text(series):
            continue
        values = series.dropna().astype(str)
        if values.empty or values.nunique() < 0.9 * len(table):
            continue
        spaced = values.str.contains(" ").mean()
        pathlike = values.str.contains(r"[/\\]|\.\w{2,4}$", regex=True).mean()
        if spaced >= 0.5 and pathlike < 0.2 and (best is None or spaced > best[0]):
            best = (spaced, str(column))
    return best[1] if best else None


def _kind_text(series: pd.Series) -> bool:
    return not (
        pd.api.types.is_numeric_dtype(series) or pd.api.types.is_datetime64_any_dtype(series)
    )


def _norm_key(series: pd.Series) -> pd.Series:
    """Khoá ghép đã chuẩn hoá: bỏ dấu, hoa thường, gộp khoảng trắng ("Sữa  Tươi" ~ "sữa tươi")."""
    text = series.astype("string").str.strip()
    mapping = {u: " ".join(fold(u).split()) for u in text.dropna().unique()}
    return text.map(mapping)


def _catalog_columns(
    sources: list[_Source], skip: set[str]
) -> list[tuple[_Source, str, set[str]]]:
    """Cột có thể là mã / tên hàng của một danh mục: gần như không trùng giá trị (xét mọi cột)."""
    found = []
    for src in sources:
        if src.name in skip:
            continue
        for column in src.table.columns:
            if column == SOURCE_COLUMN or pd.api.types.is_datetime64_any_dtype(src.table[column]):
                continue
            catalog = _norm_key(src.table[column]).dropna()
            if len(catalog) and catalog.nunique() >= 0.9 * len(catalog):
                found.append((src, str(column), set(catalog)))
    return found


def _overlap(key: pd.Series, values: set[str]) -> float:
    return float(key.dropna().isin(values).mean()) if key.notna().any() else 0.0


def _infer_code_column(
    lines_src: _Source, catalogs: list[tuple[_Source, str, set[str]]]
) -> str | None:
    """Dòng hàng không có cột mã hàng nhận ra được: tìm cột có giá trị khớp một danh mục."""
    best: tuple[float, str] | None = None
    taken = _used_columns(lines_src)
    for column in lines_src.table.columns:
        series = lines_src.table[column]
        if str(column) in taken or pd.api.types.is_datetime64_any_dtype(series):
            continue
        if pd.api.types.is_float_dtype(series) or series.nunique() < 3:
            continue
        key = _norm_key(series)
        score = max((_overlap(key, values) for _, _, values in catalogs), default=0.0)
        if score >= 0.9 and (best is None or score > best[0]):
            best = (score, str(column))
    return best[1] if best else None


_NOT_ATTRIBUTE_ROLES = frozenset(
    {"unit", "product_code", "product", "unit_price", "cost_price", "list_price", "price_new",
     "price_old", "qty", "qty_base", "points", "birth_date", "created_at"}
)


def _catalog_attributes(src: _Source, join: str, name: str | None) -> list[str]:
    """Cột phân loại của danh mục (nhóm hàng, loại, cờ thuốc kê đơn…): chữ, ít giá trị khác nhau."""
    roles = {c: r for r, cols in src.roles.items() for c in cols}
    picked = []
    for column in src.table.columns:
        series = src.table[column]
        if column in {join, name, SOURCE_COLUMN} or roles.get(column) in _NOT_ATTRIBUTE_ROLES:
            continue
        if pd.api.types.is_datetime64_any_dtype(series):
            continue
        if pd.api.types.is_float_dtype(series) and series.nunique() > 3:  # chỉ giữ cờ 0/1
            continue
        if roles.get(column) == "category" or 1 < series.nunique() <= 40:
            picked.append(str(column))
    return sorted(picked, key=lambda c: roles.get(c) != "category")


def _join_table(src: _Source, column: str) -> pd.DataFrame:
    """Bảng danh mục đánh chỉ mục theo khoá đã chuẩn hoá (mỗi khoá một dòng)."""
    table = src.table.assign(_k=_norm_key(src.table[column]))
    return table.dropna(subset=["_k"]).drop_duplicates("_k").set_index("_k")


def _attach(  # noqa: PLR0913 — tham số từ khoá, gọi ở hai nơi
    lines: pd.DataFrame,
    key: pd.Series,
    table: pd.DataFrame,
    *,
    attributes: list[str],
    source: str,
    budget: int,
    notes: list[str],
) -> int:
    """Ghép các cột phân loại theo khoá ``key``; trả số cột đã thêm (không quá ``budget``)."""
    added = 0
    for attribute in attributes:
        label = attribute if attribute not in lines.columns else f"{attribute} (danh mục)"
        if added >= budget or label in lines.columns:
            continue
        lines[label] = key.map(table[attribute])
        added += 1
        notes.append(f"phân loại {attribute!r} ghép từ {source!r} (khoá đã chuẩn hoá)")
    return added


def _match_catalogs(
    key: pd.Series, catalogs: list[tuple[_Source, str, set[str]]]
) -> list[tuple[_Source, str]]:
    """Danh mục khớp từ 80% khoá dòng hàng (cột khớp nhất), danh mục khớp nhất đứng trước."""
    best: dict[str, tuple[float, _Source, str]] = {}
    for src, column, values in catalogs:
        overlap = _overlap(key, values)
        if overlap >= 0.8 and (src.name not in best or overlap > best[src.name][0]):
            best[src.name] = (overlap, src, column)
    return [(src, column) for _, src, column in sorted(best.values(), key=lambda m: -m[0])]


def _enrich_products(
    lines: pd.DataFrame, lines_src: _Source, sources: list[_Source], skip: set[str]
) -> list[str]:
    """Ghép tên hàng (nếu chỉ có mã) và cột phân loại từ các danh mục, theo mã hàng; có bắc cầu."""
    notes: list[str] = []
    catalogs = _catalog_columns(sources, skip)
    if lines[C_PRODUCT_CODE].isna().all() and lines[C_PRODUCT].isna().all():
        column = _infer_code_column(lines_src, catalogs)  # cột mã hàng có tên lạ
        if column is None:
            return []
        lines[C_PRODUCT_CODE] = lines_src.table.loc[lines.index, column]
        notes.append(f"mã hàng nhận theo giá trị từ cột {column!r}")
    codes = lines[C_PRODUCT_CODE]
    if codes.isna().all():  # dòng hàng không có mã: ghép theo tên hàng
        codes = lines[C_PRODUCT]
    if codes.isna().all():
        return notes
    key = _norm_key(codes)
    matched = _match_catalogs(key, catalogs)
    attached, bridges = 0, []
    for src, column in matched:
        table = _join_table(src, column)
        names = src.col("product") or _name_col(table, {column, *src.roles.get("product_code", [])})
        if names and lines[C_PRODUCT].isna().mean() > 0.5:
            lines[C_PRODUCT] = key.map(table[names])
            notes.append(f"tên hàng ghép từ {src.name!r} theo mã hàng")
        attributes = _catalog_attributes(src, column, names)
        attached += _attach(
            lines, key, table, attributes=attributes, source=src.name,
            budget=_MAX_CATALOG_ATTRS - attached, notes=notes,
        )
        # cột mã khác của danh mục (SKU, mã nội bộ) làm khoá bắc cầu sang danh mục khác
        bridges += [
            _norm_key(key.map(table[c]))
            for c in table.columns
            if c not in {SOURCE_COLUMN, names} and table[c].nunique() >= 0.9 * len(table)
        ]
    used = {src.name for src, _ in matched}
    for bridge in bridges:
        for src, column, values in catalogs:
            if src.name in used or _overlap(bridge, values) < 0.8:
                continue
            used.add(src.name)
            attributes = _catalog_attributes(src, column, None)
            attached += _attach(
                lines, bridge, _join_table(src, column), attributes=attributes,
                source=src.name, budget=_MAX_CATALOG_ATTRS - attached, notes=notes,
            )
    return notes


def _used_columns(src: _Source) -> set[str]:
    """Cột gốc đã thành cột chuẩn (kể cả cột trạng thái thô: đã có trạng thái chuẩn)."""
    roles = {"order_id", "status", *(r for _, r in _LINE_FIELDS), *(r for _, r in _ATTRIBUTES)}
    used = {src.col(role) for role in roles} | {src.date, _code_col(src), SOURCE_COLUMN}
    return {str(c) for c in used if c}


def _extras(table: pd.DataFrame, src: _Source, taken: set[str]) -> pd.DataFrame:
    """Các cột còn lại của bảng gốc, giữ tên gốc (đổi tên nếu trùng cột chuẩn)."""
    columns = [c for c in table.columns if str(c) not in _used_columns(src)]
    rename = {c: f"{c} (gốc)" for c in columns if str(c) in taken}
    return table[columns].rename(columns=rename)


def _order_extras(src: _Source, ids: pd.Series, taken: set[str]) -> pd.DataFrame:
    """Cột phụ không đổi trong một đơn (thuộc tính của đơn), một dòng mỗi mã đơn."""
    extra = _extras(src.table, src, taken)
    if extra.empty:
        return extra
    extra = extra.assign(_k=ids.to_numpy())
    # cột đổi theo dòng mới là thuộc tính của dòng; vài đơn nhập lặp lệch số không làm mất cả cột
    varying = extra.groupby("_k").nunique(dropna=False).gt(1).mean() > 0.05
    keep = [c for c in extra.columns if c != "_k" and not varying.get(c, False)]
    return extra[[*keep, "_k"]].drop_duplicates("_k").set_index("_k")


def _lines_frame(src: _Source, *, by_order: bool) -> tuple[pd.DataFrame, int]:
    """Dòng hàng của bảng ``src``; bỏ dòng lặp nguyên văn nếu bảng ghi theo đơn."""
    table = src.table
    if by_order:
        keep = ~table.drop(columns=[SOURCE_COLUMN], errors="ignore").duplicated(keep="first")
        table = table[keep.to_numpy()]
    order_col = src.col("order_id")
    frame = pd.DataFrame(
        {C_ORDER: _key(table[order_col]).to_numpy() if order_col else pd.NA}, index=table.index
    )
    for name, role in _LINE_FIELDS:
        column = src.col(role)
        frame[name] = table[column] if column else pd.NA
    if frame[C_QTY_BASE].isna().all():
        frame[C_QTY_BASE] = frame[C_QTY]
    # rulebook §5: giá vốn ghi trên dòng bán là cho MỘT đơn vị bán (cùng đơn vị với đơn giá)
    has_cost = frame[C_COST].notna().any() and frame[C_QTY].notna().any()
    frame[C_PROFIT] = frame[C_AMOUNT] - frame[C_QTY] * frame[C_COST] if has_cost else pd.NA
    code = _code_col(src)
    frame[C_PRODUCT_CODE] = table[code] if code else pd.NA
    extra = _extras(table, src, set(_LINE_ORDER))
    frame = pd.concat([frame, extra], axis=1)
    return frame, len(src.table) - len(table)


def _orders_frame(
    head: _Source, fallback_status: pd.Series | None, labels: Mapping[str, str]
) -> pd.DataFrame:
    orders = pd.DataFrame({C_ORDER: _key(head.table[head.col("order_id")]).to_numpy()})
    orders[C_DATE] = head.table[head.date].to_numpy() if head.date else pd.NaT
    status = _status(head, labels)
    status = fallback_status if status is None else status
    orders[C_STATUS] = pd.NA if status is None else status.to_numpy()
    for name, role in _ATTRIBUTES:
        column = head.col(role)
        if column:
            orders[name] = head.table[column].to_numpy()
    orders = orders.drop_duplicates(C_ORDER).reset_index(drop=True)
    extra = _order_extras(head, _key(head.table[head.col("order_id")]), set(_ORDER_COLUMNS))
    for column in extra.columns:
        orders[column] = orders[C_ORDER].map(extra[column])
    return orders


def _sales_book(src: _Source, spec: RuleSpec, labels: Mapping[str, str]) -> Canonical:
    """Sổ bán hàng không có mã đơn: chỉ có bảng dòng hàng, mỗi dòng là một lần ghi."""
    lines, _ = _lines_frame(src, by_order=False)
    lines[C_DATE] = src.table[src.date].to_numpy()
    status = _status(src, labels)
    lines[C_STATUS] = pd.NA if status is None else status.to_numpy()
    lines[C_COUNTS] = _counts_flag(status, lines[C_ORDER], set(), spec).to_numpy()
    note = f"sổ bán hàng {src.name!r} không có mã đơn: chỉ có {LINES}, mỗi dòng là một lần ghi"
    columns = _LINE_ORDER + [c for c in lines.columns if c not in _LINE_ORDER]
    book = _with_views({LINES: lines[columns].reset_index(drop=True)})
    return Canonical(book, (note,), (src.name,))


def _is_ledger(src: _Source) -> bool:
    """Sổ ghi theo lượt (vd. sổ sửa xe): mỗi dòng một lượt có ngày và tiền, không mã đơn."""
    return bool(
        not src.col("order_id") and src.col("line_amount") and src.date and not src.has_item()
    )


def _ledger(src: _Source, spec: RuleSpec, labels: Mapping[str, str]) -> Canonical:
    """Mỗi dòng sổ là một lượt (phiếu): bảng đơn có mã đơn là số dòng, doanh thu là tiền."""
    table = src.table
    orders = pd.DataFrame({C_ORDER: [f"L{i}" for i in range(len(table))]}, index=table.index)
    orders[C_DATE] = table[src.date]
    status = _status(src, labels)
    orders[C_STATUS] = pd.NA if status is None else status
    orders[C_REVENUE] = table[src.col("line_amount")]
    orders[C_NLINES] = 1
    orders[C_COUNTS] = _counts_flag(status, orders[C_ORDER], set(), spec).to_numpy()
    extra = _extras(table, src, set(orders.columns))
    orders = pd.concat([orders, extra], axis=1).reset_index(drop=True)
    note = f"sổ {src.name!r} không có mã đơn: mỗi dòng là một lượt / phiếu ({ORDERS})"
    return Canonical(_with_views({ORDERS: orders}), (note,), (src.name,))


def _orders_only(
    head: _Source, sources: list[_Source], spec: RuleSpec, labels: Mapping[str, str]
) -> Canonical:
    """Chỉ có bảng đơn (không có dòng hàng): doanh thu đơn lấy từ cột tiền hàng của đơn."""
    orders = _orders_frame(head, None, labels)
    amount = head.col("order_subtotal") or head.col("order_total")
    by_id = head.table.assign(_k=_key(head.table[head.col("order_id")])).drop_duplicates("_k")
    orders[C_REVENUE] = orders[C_ORDER].map(by_id.set_index("_k")[amount]) if amount else pd.NA
    status = orders[C_STATUS] if orders[C_STATUS].notna().any() else None
    returned = _returned_orders(sources)
    orders[C_COUNTS] = _counts_flag(status, orders[C_ORDER], returned, spec).to_numpy()
    note = f"chỉ có bảng đơn {head.name!r} (không có dòng hàng): doanh thu đơn lấy từ {amount!r}"
    return Canonical(_with_views({ORDERS: orders}), (note,), (head.name,))


def _finish(
    tables: dict[str, pd.DataFrame], sources: list[_Source], notes: list[str], replaces: list[str]
) -> Canonical:
    """Thêm bảng nhập hàng, bảng đã lọc và bản đồ tên cột gốc → tên chuẩn."""
    notes.extend(_add_imports(tables, sources, set(replaces[:2])))
    used = [s for s in sources if s.name in set(replaces)]
    return Canonical(
        _with_views(tables), tuple(notes), tuple(dict.fromkeys(replaces)), _renames(used)
    )


def build_canonical(
    tables: dict[str, pd.DataFrame],
    spec: RuleSpec = DEFAULT_SPEC,
    labels: Mapping[str, str] | None = None,
) -> Canonical:
    """Dựng ``don_chuan`` và ``dong_hang_chuan`` từ các bảng gốc; rỗng nếu không đủ vai trò.

    ``labels``: nhãn trạng thái chuẩn cho các cách ghi lạ (xem labels.py).
    """
    labels = labels or {}
    sources = _sources(tables)
    _infer_order_ids(sources)
    lines_src = _largest([s for s in sources if _is_lines(s)])
    if lines_src is None:
        book = _largest([s for s in sources if _is_sales_book(s)])
        if book is not None:
            return _sales_book(book, spec, labels)
        head_only = _largest([s for s in sources if _is_header(s)])
        if head_only is not None:
            return _orders_only(head_only, sources, spec, labels)
        ledger = _largest([s for s in sources if _is_ledger(s)])
        if ledger is not None:
            return _ledger(ledger, spec, labels)
        return Canonical({}, ("không có bảng dòng hàng, sổ bán hàng hay bảng đơn dùng được",))
    header_src = _largest([s for s in sources if _is_header(s) and s.name != lines_src.name])
    head = header_src or lines_src
    if head.date is None:
        return Canonical({}, (f"bảng {head.name!r} không có cột ngày đặt",))
    notes = [
        f"dòng hàng từ {lines_src.name!r}",
        f"đơn từ {head.name!r}" + ("" if header_src else " (bảng phẳng)"),
    ]

    lines, removed = _lines_frame(lines_src, by_order=True)
    if removed:
        notes.append(f"đã bỏ {removed} dòng lặp nguyên văn trong cùng đơn (rulebook §8)")
    orders = _orders_frame(head, _status(lines_src, labels), labels)

    codes = _group_by_customer_code(sources)
    if codes is not None and C_CUSTOMER_CODE in orders:
        orders[C_GROUP] = _key(orders[C_CUSTOMER_CODE]).map(codes)

    revenue = lines.groupby(C_ORDER)[C_AMOUNT].sum(min_count=1)
    orders[C_REVENUE] = orders[C_ORDER].map(revenue)
    subtotal = header_src.col("order_subtotal") if header_src else None
    if header_src is not None and subtotal:  # đơn không có dòng chi tiết: dùng tiền hàng của đơn
        by_id = header_src.table.assign(_k=_key(header_src.table[header_src.col("order_id")]))
        fallback = orders[C_ORDER].map(by_id.drop_duplicates("_k").set_index("_k")[subtotal])
        orders[C_REVENUE] = orders[C_REVENUE].fillna(fallback)
    orders[C_NLINES] = orders[C_ORDER].map(lines.groupby(C_ORDER).size()).fillna(0).astype(int)

    status = orders[C_STATUS] if orders[C_STATUS].notna().any() else None
    returned = _returned_orders(sources)
    orders[C_COUNTS] = _counts_flag(status, orders[C_ORDER], returned, spec).to_numpy()

    notes.extend(_enrich_products(lines, lines_src, sources, {lines_src.name, head.name}))
    shifted = _add_shift(orders, head, spec) if head.col("order_id") else False
    _add_customer_identity(orders, sources)
    _add_staff_names(orders, sources)
    payments, payment_name = _add_payments(
        orders, head, sources, {lines_src.name, head.name}
    )
    by_order = orders.set_index(C_ORDER)
    for name in (C_DATE, C_STATUS, C_COUNTS, *((C_SHIFT,) if shifted else ())):
        lines[name] = lines[C_ORDER].map(by_order[name])
    lines[C_COUNTS] = lines[C_COUNTS].fillna(False).astype(bool)
    columns = _LINE_ORDER + [c for c in lines.columns if c not in _LINE_ORDER]
    tables_out = {ORDERS: orders, LINES: lines[columns].reset_index(drop=True)}
    replaces = [lines_src.name, head.name]
    if payments is not None and payment_name:
        tables_out[PAYMENTS] = payments
        replaces.append(payment_name)
        notes.append(f"các lần khách trả tiền từ {payment_name!r}")
    return _finish(tables_out, sources, notes, replaces)
