"""Vẽ sơ đồ tổng quan pipeline DataMate (SVG) kèm ví dụ vào / ra. Chạy: python scripts/_draw_pipeline.py"""

from __future__ import annotations

from html import escape
from pathlib import Path

OUT = Path(__file__).resolve().parents[1] / "reports" / "pipeline_overview.svg"
W, H = 1600, 980
INK, MUTED, LINE, BG, SOFT = "#1c2521", "#5d6a63", "#cfd6d0", "#ffffff", "#f6f7f5"
CODE, CODE_BG = "#1d6b66", "#e3f0ee"
LLM, LLM_BG = "#a8481a", "#f8e9de"
CACHE, CACHE_BG = "#4b5a8f", "#e6e9f4"
OK, OK_BG = "#2c6e3a", "#e2f1e5"
TAGS = {"code": ("CODE", CODE, CODE_BG), "llm": ("LLM", LLM, LLM_BG), "cache": ("CACHE", CACHE, CACHE_BG)}
MONO = "Consolas, 'Courier New', monospace"

parts: list[str] = []


def wrap(s: str, width: float, size: float, mono: bool = False) -> list[str]:
    """Ngắt dòng theo độ rộng ước lượng (tiếng Việt có dấu rộng khoảng 0,56 cỡ chữ)."""
    per = size * (0.62 if mono else 0.56)
    limit = max(8, int(width / per))
    lines, cur = [], ""
    for word in s.split(" "):
        trial = f"{cur} {word}".strip()
        if len(trial) <= limit:
            cur = trial
        else:
            lines.append(cur)
            cur = word
    if cur:
        lines.append(cur)
    return lines


def text(x: float, y: float, s: str, size: float = 14, weight: int = 400, fill: str = INK,
         anchor: str = "start", mono: bool = False) -> None:
    family = f' font-family="{MONO}"' if mono else ""
    parts.append(
        f'<text x="{x}" y="{y}" font-size="{size}" font-weight="{weight}" fill="{fill}" '
        f'text-anchor="{anchor}"{family}>{escape(s)}</text>'
    )


def rect(x: float, y: float, w: float, h: float, fill: str, stroke: str = LINE, r: int = 12,
         dash: str = "", sw: float = 1.5) -> None:
    extra = f' stroke-dasharray="{dash}"' if dash else ""
    parts.append(
        f'<rect x="{x}" y="{y}" width="{w}" height="{h}" rx="{r}" fill="{fill}" stroke="{stroke}" '
        f'stroke-width="{sw}"{extra}/>'
    )


def tag(x: float, y: float, kind: str) -> float:
    label, color, bg = TAGS[kind]
    width = 12 + 7.6 * len(label)
    rect(x, y - 13, width, 19, bg, color, 5, sw=1)
    text(x + width / 2, y + 1, label, 10.5, 700, color, "middle")
    return width


def arrow(x1: float, y: float, x2: float) -> None:
    parts.append(f'<line x1="{x1}" y1="{y}" x2="{x2 - 9}" y2="{y}" stroke="{MUTED}" stroke-width="2.4"/>')
    parts.append(f'<polygon points="{x2},{y} {x2 - 11},{y - 6} {x2 - 11},{y + 6}" fill="{MUTED}"/>')


def bullets(x: float, y: float, w: float, items: list[tuple[str | None, str, bool]]) -> float:
    for kind, s, planned in items:
        offset = 0.0
        if kind:
            offset = tag(x, y, kind) + 7
        lines = wrap(s, w - offset, 13)
        if planned:  # bước đề xuất, chưa cài đặt
            rect(x - 6, y - 17, w + 8, 20 * len(lines) + 12, "#fffaf0", "#c9a227", 8, dash="5 4", sw=1.2)
        for i, line in enumerate(lines):
            text(x + offset, y + i * 19, line, 13, 400, MUTED if planned else INK)
        y += 19 * len(lines) + 14
    return y


def example(x: float, y: float, w: float, h: float, vao: list[str], ra: list[str], accent: str) -> None:
    rect(x, y, w, h, "#fbfbf8", accent, 10, dash="6 4", sw=1.3)
    text(x + 12, y + 20, "VÍ DỤ", 11, 700, accent)
    cy = y + 42
    text(x + 12, cy, "VÀO", 11, 700, MUTED)
    for line in vao:
        cy += 17
        text(x + 12, cy, line, 11.5, 400, INK, mono=True)
    cy += 26
    text(x + 12, cy, "RA", 11, 700, accent)
    for line in ra:
        cy += 17
        text(x + 12, cy, line, 11.5, 400, INK, mono=True)


def card(x: float, y: float, w: float, h: float, num: str, title: str, sub: str, accent: str) -> None:
    rect(x, y, w, h, BG, LINE, 14)
    parts.append(f'<rect x="{x}" y="{y}" width="{w}" height="8" rx="4" fill="{accent}"/>')
    text(x + 16, y + 38, f"{num} {title}", 19, 700)
    text(x + 16, y + 58, sub, 12.5, 400, MUTED)


# --- nền, tiêu đề, chú giải
parts.append(f'<rect width="{W}" height="{H}" fill="{BG}"/>')
text(40, 50, "DataMate · Agent trả lời câu hỏi về dữ liệu cửa hàng nhỏ", 29, 700)
text(40, 78, "Hai bộ giải độc lập (pandas và SQL) trên bảng chuẩn tắc. Code lo phần chắc chắn; LLM lo phần mơ hồ nhưng luôn có code kiểm chứng.", 14.5, 400, MUTED)
lx = 40
for kind, note in (("code", "xử lý bằng code"), ("llm", "gọi mô hình ngôn ngữ"), ("cache", "tính một lần, dùng lại")):
    w = tag(lx, 108, kind)
    text(lx + w + 8, 112, note, 12.5, 400, MUTED)
    lx += w + 8 + 7.4 * len(note) + 26
rect(lx, 94, 22, 18, "#fffaf0", "#c9a227", 5, dash="4 3", sw=1.2)
text(lx + 30, 108, "đề xuất, đang đo thử (chưa dùng khi nộp)", 12.5, 400, MUTED)

# --- thanh đầu vào
rect(40, 128, 1520, 50, SOFT, LINE, 12)
text(58, 150, "ĐẦU VÀO", 12, 700, MUTED)
text(58, 169, "Dữ liệu doanh nghiệp (CSV · XLSX · SQLite, nhiều bảng) · README mô tả cột · Rulebook (định nghĩa doanh thu, công nợ, ca, khách…) · Câu hỏi tiếng Việt đời thường + ngày hiện tại", 13.5, 400, INK)

top, ch, cw, gap = 196, 676, 284, 25
xs = [40 + i * (cw + gap) for i in range(5)]
inner = cw - 32

# ① chuẩn bị dữ liệu
x = xs[0]
card(x, top, cw, ch, "①", "Chuẩn bị dữ liệu", "một lần cho mỗi doanh nghiệp", CODE)
y = bullets(x + 16, top + 92, inner, [
    ("code", "Nạp và làm sạch: gộp bảng chia theo tháng, đặt kiểu ngày / số", False),
    ("code", "Nhận vai trò cột theo tên và theo giá trị", False),
    ("llm", "Đề xuất vai trò cho cột tên lạ; code kiểm chứng bằng giá trị mới dùng", False),
    ("llm", "Gán nhãn trạng thái đơn lạ (hoàn thành / huỷ / trả / đang giao)", False),
    ("code", "Dựng bảng chuẩn tắc theo rulebook: đơn, dòng hàng, thanh toán, nhập hàng, bản đã lọc", False),
])
example(x + 12, y + 4, cw - 24, top + ch - y - 16, [
    "12 bảng BanHang_T1..T12",
    "Ghi chú: cancel | Huỷ | (trống)",
    "Khách: Nguyễn Văn A | Khách lẻ",
], [
    "don_chuan (1 dòng = 1 đơn)",
    "Trạng thái chuẩn: huy |",
    "  hoan_thanh (trống = hoàn thành)",
    "Khách định danh: A ;",
    "  Khách lẻ → rỗng (không đếm)",
    "+ bản đã lọc đơn tính doanh thu",
], CODE)

# ② hiểu câu hỏi
x = xs[1]
card(x, top, cw, ch, "②", "Hiểu câu hỏi", "mỗi câu hỏi", CODE)
y = bullets(x + 16, top + 92, inner, [
    ("code", "Chuẩn hoá: mở rộng viết tắt, sửa Telex", False),
    ("code", "Gợi ý khoảng ngày: hôm nay, 3/25, cùng kỳ, N ngày kể từ…", False),
    ("code", "Khớp tên hàng, khách, nhóm trong dữ liệu", False),
    ("code", "Luật \"không thể trả lời\"", False),
    ("llm", "Làm rõ: dạng đáp án, bảng cần dùng; code kiểm chứng", True),
])
example(x + 12, y + 4, cw - 24, top + ch - y - 16, [
    "Th 9/25 ai là khách mua",
    "nhiều lần nhất? (nay 2026-07-08)",
], [
    "tháng 9/25 ai là khách… (viết lại)",
    "tháng 9/2025 = 2025-09-01 →",
    "  2025-09-30",
    "SQL: BETWEEN DATE '2025-09-01'",
    "     AND DATE '2025-09-30'",
    "pandas: P.between('2025-09-01',",
    "                 '2025-09-30')",
], CODE)

# ③ giải
x = xs[2]
card(x, top, cw, ch, "③", "Giải: hai bộ giải", "luân phiên, tối đa 4 lần sinh", LLM)
for k, (name, sub) in enumerate((("pandas", "Python, sandbox"), ("SQL", "DuckDB, chỉ đọc"))):
    bx = x + 16 + k * 127
    rect(bx, top + 78, 117, 48, LLM_BG, LLM, 10)
    text(bx + 58, top + 99, name, 16, 700, LLM, "middle")
    text(bx + 58, top + 117, sub, 11, 400, MUTED, "middle")
y = bullets(x + 16, top + 158, inner, [
    ("llm", "Sinh code từ prompt: bảng chuẩn, rulebook, ví dụ mẫu, gợi ý", False),
    ("code", "Chạy trong sandbox giới hạn thời gian", False),
    ("code", "Kiểm tra luật rẻ: dùng nhầm bảng, so ngưỡng theo ngày sai, kết quả 0", False),
    ("llm", "Sửa lỗi kèm gợi ý cụ thể, tối đa 3 lần", False),
])
example(x + 12, y + 4, cw - 24, top + ch - y - 16, [
    "gợi ý thời gian + mô tả bảng",
    "chuẩn + rulebook + ví dụ mẫu",
], [
    'd = T["don_tinh_doanh_thu"]',
    'd = d[P.between(..).contains(',
    '    d["Ngày đặt"]) &',
    '    d["Khách định danh"].notna()]',
    'top = d.groupby("Khách định danh")',
    '  ["Mã đơn"].nunique().idxmax()',
    'answer = {"type": "string", ...}',
], LLM)

# ④ quyết định
x = xs[3]
card(x, top, cw, ch, "④", "Quyết định", "bằng code", CODE)
y = bullets(x + 16, top + 92, inner, [
    ("code", "Bỏ phiếu: cần 2 đáp án giống nhau từ 2 bộ giải khác nhau", False),
    ("code", "Kiểm tra hợp lý: khách lẻ không phải khách, tên có trong dữ liệu, % bất thường", False),
    ("code", "Không đủ chắc thì abstain: 0 điểm, không bị trừ", False),
])
example(x + 12, y + 4, cw - 24, top + ch - y - 16, [
    "pandas → 'Nguyễn Văn A'",
    "SQL    → 'Nguyễn Văn A'",
], [
    "2 nguồn khác nhau, cùng đáp án",
    '→ {"type": "string",',
    '   "answer": "Nguyễn Văn A"}',
    "",
    "nếu lệch: pandas 7 ≠ SQL 9",
    "→ abstain (0 điểm)",
], CODE)

# ⑤ đầu ra
x = xs[4]
card(x, top, cw, ch, "⑤", "Đầu ra", "để nộp và để phân tích", OK)
y = bullets(x + 16, top + 92, inner, [
    (None, "submission.jsonl: number · percent · string · date · boolean · list · table · unanswerable · abstain", False),
    (None, "validate_submission: đủ id, không trùng, đúng kiểu và định dạng", False),
    (None, "Nhật ký từng câu: các lần sinh, nguồn, vết từng bước, thời gian, lỗi", False),
])
example(x + 12, y + 4, cw - 24, top + ch - y - 16, [
    "đáp án chốt của câu hỏi",
], [
    '{"id": "q_…",',
    ' "type": "string",',
    ' "answer": "Nguyễn Văn A"}',
    "",
    "dùng nhật ký để: phân loại lỗi",
    "theo doanh nghiệp, loại câu,",
    "tìm điểm nghẽn rồi sửa",
], OK)

# mũi tên giữa các thẻ
for i in range(4):
    arrow(xs[i] + cw + 2, top + 28, xs[i + 1] - 2)

# chân trang
fy = top + ch + 20
rect(40, fy, 1520, 62, SOFT, LINE, 12)
text(58, fy + 24, "Nguyên tắc thiết kế", 13.5, 700)
text(58, fy + 46, "Dữ kiện tách khỏi luật (rulebook là dữ liệu) · LLM chỉ đề xuất, code kiểm chứng · ngăn lỗi từ cấu trúc hơn là phát hiện sau · đo trên dev và holdout.  Tên và số trong ví dụ là minh hoạ.", 12.5, 400, MUTED)

body = "\n".join(parts)
OUT.parent.mkdir(exist_ok=True)
OUT.write_text(
    f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {W} {H}" width="{W}" height="{H}" '
    f'font-family="Segoe UI, Arial, sans-serif">\n{body}\n</svg>\n',
    encoding="utf-8",
)
print("da ghi", OUT)
