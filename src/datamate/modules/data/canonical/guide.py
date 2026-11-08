"""Lời mô tả bảng chuẩn tắc cho LLM: cột nào nghĩa gì và khi nào dùng bảng nào."""

# ruff: noqa: E501  (văn bản prompt, ngắt dòng làm đổi nghĩa khi đọc)

from __future__ import annotations

from datamate.modules.data.canonical.build import (
    C_AFTER,
    C_AMOUNT,
    C_CLIENT_ID,
    C_CLIENT_NAME,
    C_COST,
    C_COUNTS,
    C_DATE,
    C_DEBT_ORDER,
    C_GROUP,
    C_IMPORT_AMOUNT,
    C_IMPORT_DATE,
    C_IMPORT_PRICE,
    C_IMPORT_QTY,
    C_IMPORT_STATUS,
    C_IMPORT_UNIT,
    C_NEW_DEBT,
    C_ORDER,
    C_PAID,
    C_PAID_ON,
    C_PAID_SAME_DAY,
    C_PRODUCT,
    C_PROFIT,
    C_QTY_BASE,
    C_REPAY,
    C_REVENUE,
    C_SHIFT,
    C_STATUS,
    C_TIME,
    C_TOTAL,
    IMPORTS,
    LINES,
    ORDERS,
    PAYMENTS,
    VIEW_LINES,
    VIEW_ORDERS,
    Canonical,
)

_HEADER = (
    "# Bảng chuẩn tắc (code dựng sẵn từ các bảng gốc, đã áp dụng định nghĩa của RULEBOOK)\n"
    "ƯU TIÊN dùng các bảng này cho câu về đơn, doanh thu, số đơn, số lượng, lãi gộp, xếp hạng hàng/khách. "
    "Bảng gốc chỉ dùng cho thông tin chúng không có (nhập hàng, tồn kho, chi phí...).\n"
    f"CÁCH CHỌN BẢNG: đếm đơn, doanh thu, số lượng bán, lãi gộp, trung bình mỗi đơn → dùng bảng ĐÃ LỌC "
    f"{VIEW_ORDERS} (một dòng một đơn) hoặc {VIEW_LINES} (một dòng một dòng hàng), KHÔNG cần lọc "
    f"cờ \"Tính vào doanh thu\" nữa. CÂU CÓ ĐIỀU KIỆN VỀ HÀNG (tên hàng, nhóm hàng, loại, size, đơn vị) → "
    f"dùng bảng dòng hàng {VIEW_LINES} và cột \"Thành tiền dòng\" / \"Số lượng\". "
    f"Đơn huỷ, đơn trả hàng, tỉ lệ huỷ/trả, công nợ → dùng bảng đầy đủ "
    f"({ORDERS}, {LINES}, {PAYMENTS}) vì cần cả đơn không tính doanh thu."
)

_ORDERS_DOC = f"""\
{ORDERS} — mỗi dòng MỘT đơn (đã bỏ dòng lặp nguyên văn của cùng một đơn):
  - "{C_ORDER}": mã đơn
  - "{C_DATE}": ngày đặt đơn
  - "{C_STATUS}": hoan_thanh | huy | tra_hang | dang_giao | khac (đã chuẩn hoá mọi cách ghi)
  - "{C_COUNTS}": TRUE nếu đơn tính vào doanh thu / số đơn (không huỷ, không trả kể cả trả một phần)
  - "{C_REVENUE}": doanh thu đơn = tổng thành tiền các dòng hàng (KHÔNG trừ giảm giá cả đơn)
  - các cột "Khách", "Mã khách", "{C_GROUP}", "Hình thức thanh toán", "Nhân viên" nếu dữ liệu có
  - "{C_CLIENT_ID}" / "{C_CLIENT_NAME}": khách định danh theo rulebook §3 (rỗng với khách lẻ):
    đếm / xếp hạng khách PHẢI nhóm theo "{C_CLIENT_ID}" và bỏ dòng rỗng; trả lời "ai" bằng "{C_CLIENT_NAME}"
  - "{C_SHIFT}" (sáng / chiều / ngoài ca) và "{C_TIME}" (giờ đặt đơn), nếu dữ liệu có giờ tạo đơn
  LƯU Ý: bảng đơn KHÔNG có cột về hàng (tên hàng, nhóm hàng, số lượng, thành tiền dòng). Lọc theo
  mặt hàng / nhóm hàng phải dùng bảng dòng hàng, và đếm đơn bằng số "{C_ORDER}" khác nhau.
  → Số đơn = COUNT(*) trên {VIEW_ORDERS}; doanh thu = SUM("{C_REVENUE}") trên {VIEW_ORDERS};
    số đơn huỷ = đếm "{C_STATUS}" = 'huy' trên {ORDERS} (bảng đầy đủ);
    tỉ lệ huỷ = đơn huỷ / MỌI đơn đặt trong kỳ (mọi trạng thái) trên {ORDERS};
    theo ca: lọc "{C_SHIFT}" (không tự đoán giờ)."""

_LINES_DOC = f"""\
{LINES} — mỗi dòng MỘT dòng hàng của đơn:
  - "{C_ORDER}", "{C_DATE}", "{C_STATUS}", "{C_COUNTS}": như ở {ORDERS} (của đơn chứa dòng này)
  - "{C_PRODUCT}": tên hàng; "Số lượng": theo đơn vị ghi trên dòng
  - "{C_QTY_BASE}": số lượng quy về đơn vị cơ bản (dùng cho "bán chạy", tổng số lượng)
  - "{C_AMOUNT}": thành tiền của dòng; "Đơn giá": đơn giá ghi trên dòng
  → Doanh thu một mặt hàng = SUM("{C_AMOUNT}") trên {VIEW_LINES};
    bán chạy / tổng số lượng = SUM("{C_QTY_BASE}") trên {VIEW_LINES}.
  - "Mã hàng"; các cột nhóm / loại hàng (nếu có) được ghép từ danh mục hàng: dùng cho câu "nhóm hàng X", "tỉ trọng nhóm".
    "{C_GROUP}" ở bảng đơn là nhóm KHÁCH, không phải nhóm hàng.
  - "{C_COST}": giá vốn MỘT đơn vị bán ghi trên dòng (nếu có); "{C_PROFIT}" = thành tiền − số lượng × giá vốn
  → Lãi gộp = SUM("{C_PROFIT}") trên {VIEW_LINES} (không tính lại giá vốn từ phiếu nhập)."""

_DEBT_ORDERS_DOC = f"""  Cột công nợ của {ORDERS}: "{C_DEBT_ORDER}" (đơn có hình thức thanh toán ghi nợ), "{C_TOTAL}" (tổng khách
  phải trả), "{C_PAID_SAME_DAY}" (đã trả trong ngày mua), "{C_NEW_DEBT}" (phần chưa trả ngay của đơn ghi nợ
  không huỷ). Nợ thêm trong kỳ = SUM("{C_NEW_DEBT}") của đơn đặt trong kỳ."""

_PAYMENTS_DOC = f"""{PAYMENTS} — mỗi dòng MỘT lần khách trả tiền cho một đơn:
  - "{C_ORDER}", "{C_PAID_ON}" (ngày giờ thu), "{C_PAID}" (số tiền), "Hình thức thu"
  - "{C_DATE}", "{C_STATUS}", "{C_DEBT_ORDER}": ngày đặt, trạng thái, đơn có ghi nợ không (của đơn được trả)
  - "{C_AFTER}": ngày thu sau ngày mua; "{C_REPAY}": TRUE nếu là trả nợ (đơn ghi nợ, không huỷ, thu sau ngày mua)
  - "{C_CLIENT_ID}", "{C_CLIENT_NAME}": khách của đơn được trả (rỗng với khách lẻ)
  → Trả nợ / thu nợ trong kỳ = SUM("{C_PAID}") với "{C_REPAY}" và "{C_PAID_ON}" trong kỳ (kể cả đơn kỳ trước).
    Tiền trả cùng ngày mua là trả lúc mua, không phải trả nợ.
    Dư nợ của khách đến hết ngày D = SUM("{C_NEW_DEBT}") của đơn đặt đến D (bảng {ORDERS}) trừ
    SUM("{C_PAID}") với "{C_REPAY}" và "{C_PAID_ON}" đến D, nhóm theo "{C_CLIENT_ID}" (xem ví dụ)."""

_IMPORTS_DOC = f"""{IMPORTS} — mỗi dòng MỘT dòng hàng của phiếu nhập:
  - "Mã phiếu nhập", "{C_IMPORT_DATE}", "{C_IMPORT_STATUS}" (huy = phiếu huỷ), "Tên hàng"
  - "{C_IMPORT_QTY}", "{C_IMPORT_UNIT}" (đơn vị nhập), "{C_IMPORT_PRICE}", "{C_IMPORT_AMOUNT}"
  → Giá nhập bình quân một mặt hàng trong tháng = SUM("{C_IMPORT_AMOUNT}") / SUM("{C_IMPORT_QTY}")
    (bình quân theo SỐ LƯỢNG nhập, không phải trung bình cộng các mức giá), theo đơn vị nhập được
    hỏi, phiếu có "{C_IMPORT_DATE}" trong tháng, bỏ phiếu huỷ ("{C_IMPORT_STATUS}" = 'huy')."""


def _renames_doc(canonical: Canonical) -> str:
    pairs = [f'"{old}" → "{new}"' for old, new in canonical.renames[:24]]
    if not pairs:
        return ""
    return (
        "README và các bảng gốc gọi cột bằng TÊN GỐC; trong bảng chuẩn tắc cột đã đổi tên:\n  "
        + "; ".join(pairs)
        + '\nNối bảng chuẩn tắc với bảng gốc (tồn kho, nhập hàng…) qua "Mã hàng" ↔ cột mã hàng của'
        " bảng gốc."
    )


def render_guide(canonical: Canonical) -> str:
    """Phần đầu mô tả bảng; chuỗi rỗng nếu không dựng được bảng chuẩn tắc."""
    if not canonical.tables:
        return ""
    parts = [_HEADER]
    if ORDERS in canonical.tables:
        parts.append(_ORDERS_DOC)
        if PAYMENTS in canonical.tables:
            parts.append(_DEBT_ORDERS_DOC)
    if PAYMENTS in canonical.tables:
        parts.append(_PAYMENTS_DOC)
    if IMPORTS in canonical.tables:
        parts.append(_IMPORTS_DOC)
    if LINES in canonical.tables:
        parts.append(_LINES_DOC)
    if ORDERS not in canonical.tables:
        parts.append(
            "(Dữ liệu này không có mã đơn: mỗi dòng hàng là một lần ghi, không đếm được số đơn.)"
        )
    if _renames_doc(canonical):
        parts.append(_renames_doc(canonical))
    parts.append("Nguồn: " + "; ".join(canonical.notes))
    return "\n\n".join(parts)
