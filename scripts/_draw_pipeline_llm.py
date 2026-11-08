"""Vẽ sơ đồ pipeline DataMate với LLM ở mọi bước (SVG). Chạy: python scripts/_draw_pipeline_llm.py"""

from __future__ import annotations

from html import escape
from pathlib import Path

OUT = Path(__file__).resolve().parents[1] / "reports" / "pipeline_llm_overview.svg"
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


# --- background, title, legend
PROPOSED, PROPOSED_BG = "#c9a227", "#fffaf0"
parts.append(f'<rect width="{W}" height="{H}" fill="{BG}"/>')
text(40, 50, "DataMate · LLM at every step, verified by code", 29, 700)
text(40, 78, "Mỗi bước dùng LLM cho phần mơ hồ; deterministic code luôn verify đầu ra của LLM. LLM đề xuất, code quyết định.", 14.5, 400, MUTED)
lx = 40
for kind, note in (("code", "deterministic code"), ("llm", "LLM call"), ("cache", "computed once, cached")):
    w = tag(lx, 108, kind)
    text(lx + w + 8, 112, note, 12.5, 400, MUTED)
    lx += w + 8 + 7.4 * len(note) + 26
rect(lx, 94, 22, 18, PROPOSED_BG, PROPOSED, 5, dash="4 3", sw=1.2)
text(lx + 30, 108, "proposed: chưa dùng khi nộp, đang đo", 12.5, 400, MUTED)

rect(40, 128, 1520, 50, SOFT, LINE, 12)
text(58, 150, "INPUT", 12, 700, MUTED)
text(58, 169, "Business data (CSV · XLSX · SQLite, nhiều bảng) · README · Rulebook (định nghĩa doanh thu, công nợ, ca, khách…) · câu hỏi tiếng Việt + as-of date", 13.5, 400, INK)

top, ch, cw, gap = 196, 676, 284, 25
xs = [40 + i * (cw + gap) for i in range(5)]
inner = cw - 32


def stage(i: int, num: str, title: str, sub: str, accent: str, items: list, vao: list[str], ra: list[str]) -> None:
    x = xs[i]
    card(x, top, cw, ch, num, title, sub, accent)
    y = bullets(x + 16, top + 92, inner, items)
    example(x + 12, y + 4, cw - 24, top + ch - y - 16, vao, ra, accent)


stage(0, "①", "Data Preparation", "once per business", CODE, [
    ("code", "Ingest & clean: gộp bảng theo tháng, set dtype", False),
    ("code", "Role detection: theo tên cột + theo value", False),
    ("llm", "Role proposal cho cột tên lạ; code verify bằng value", False),
    ("llm", "Status labeling (hoàn thành / huỷ / trả / đang giao)", False),
    ("code", "Canonical tables theo rulebook: orders, order lines, payments, imports, filtered views", False),
], ["12 bảng BanHang_T1..T12", "Ghi chú: cancel | Huỷ | (trống)", "Khách: Nguyễn Văn A | Khách lẻ"],
   ["don_chuan (1 dòng = 1 đơn)", "Trạng thái chuẩn: huy |", "  hoan_thanh (trống = done)", "Khách định danh: A ;", "  Khách lẻ → rỗng", "+ filtered view (đơn tính doanh thu)"])

stage(1, "②", "Question Understanding", "per question", CODE, [
    ("code", "Normalize: expand abbreviation, fix Telex", False),
    ("code", "Time hints: hôm nay, 3/25, cùng kỳ, N ngày kể từ…", False),
    ("code", "Entity matching: tên hàng, khách, nhóm", False),
    ("code", "Unanswerable rules", False),
    ("llm", "Clarify: answer type, tables, filters; code verify (time, entity)", True),
], ["Th 9/25 ai là khách mua", "nhiều lần nhất? (nay 2026-07-08)"],
   ["answer_type: string (tên khách)", "table: don_tinh_doanh_thu", "tháng 9/2025 =", "  2025-09-01 → 2025-09-30", "SQL: BETWEEN DATE '2025-09-01'", "pandas: P.between('2025-09-01',", "                 '2025-09-30')"])

x = xs[2]
card(x, top, cw, ch, "③", "Solving", "2 independent solvers, ≤ 4 attempts", LLM)
for k, (name, sub) in enumerate((("pandas", "Python sandbox"), ("SQL", "DuckDB read-only"))):
    bx = x + 16 + k * 127
    rect(bx, top + 78, 117, 48, LLM_BG, LLM, 10)
    text(bx + 58, top + 99, name, 16, 700, LLM, "middle")
    text(bx + 58, top + 117, sub, 11, 400, MUTED, "middle")
y = bullets(x + 16, top + 158, inner, [
    ("llm", "Generate code: prompt = canonical schema + rulebook + few-shot + hints", False),
    ("code", "Execute in sandbox (timeout)", False),
    ("code", "Cheap rule checks: sai bảng, ngưỡng theo ngày, kết quả 0", False),
    ("llm", "Self-repair kèm hint cụ thể, ≤ 3 lần", False),
])
example(x + 12, y + 4, cw - 24, top + ch - y - 16, ["hints + schema + rulebook", "+ few-shot examples"], [
    'd = T["don_tinh_doanh_thu"]', 'd = d[P.between(..).contains(', '    d["Ngày đặt"]) &', '    d["Khách định danh"].notna()]',
    'top = d.groupby("Khách định danh")', '  ["Mã đơn"].nunique().idxmax()', 'answer = {"type": "string", ...}'], LLM)

stage(3, "④", "Decision", "vote, verify, abstain", CODE, [
    ("code", "Voting: 2 đáp án giống nhau từ 2 solver khác nhau", False),
    ("code", "Sanity check: khách lẻ, tên có trong data, % bất thường", False),
    ("code", "Abstain khi không chắc: score 0, không bị trừ", False),
    ("llm", "Format guard: đúng type, đơn vị, số phần tử? (đo bằng nhãn type có sẵn)", True),
    ("llm", "Re-solve khi bất đồng, rồi verify bằng execution + vote (không để LLM chọn)", True),
], ["pandas → 7", "SQL    → 9", "(bất đồng)"],
   ["re-solve → 9", "execution khớp SQL", "vote 2/3 → answer 9", "", "LLM judge chọn đáp án:", "đã đo, chỉ đúng 25% → bỏ"])

stage(4, "⑤", "Output & Feedback loop", "submit + improve", OK, [
    (None, "submission.jsonl (9 answer types) + validator", False),
    (None, "Run logs: samples, trace, errors, time", False),
    ("llm", "Error triage: cluster lỗi từ logs, đề xuất fix (offline, người duyệt)", True),
], ["run_log.jsonl (mỗi câu)", "gold answers (train)"],
   ['{"id": "q_…", "type": "string",', ' "answer": "Nguyễn Văn A"}', "", "triage: 'column not found'", "→ 91 lần → thêm hint + guide", "→ đo lại dev / holdout"])

for i in range(4):
    arrow(xs[i] + cw + 2, top + 28, xs[i + 1] - 2)

fy = top + ch + 20
rect(40, fy, 1520, 62, SOFT, LINE, 12)
text(58, fy + 24, "Design principles", 13.5, 700)
text(58, fy + 46, "LLM proposes, code verifies · rulebook là data, không hard-code · ngăn lỗi từ cấu trúc hơn phát hiện sau · LLM không được chọn đáp án khi chưa có cách verify · tên và số trong ví dụ là minh hoạ.", 12.5, 400, MUTED)

body = "\n".join(parts)
OUT.parent.mkdir(exist_ok=True)
OUT.write_text(
    f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {W} {H}" width="{W}" height="{H}" '
    f'font-family="Segoe UI, Arial, sans-serif">\n{body}\n</svg>\n',
    encoding="utf-8",
)
print("da ghi", OUT)
