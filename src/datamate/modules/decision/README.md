# `decision/` — TẦNG 4: kiểm tra & quyết định

Nhận các đáp án ứng viên từ `solvers/` và quyết định: **trả lời**, `unanswerable`, hay
**abstain**. Điểm PA cho +1 khi đúng, 0 khi abstain, −1 khi sai, nên tầng này quyết định độ
chính xác trên các câu đã trả lời.

**Được import:** mọi tầng thấp hơn (`core`, `infrastructure`, `domain`, `data`, `understanding`,
`solvers`). Chỉ `app/` được import tầng này.

## Đã có: `consensus/` — bỏ phiếu

| File | Việc |
|---|---|
| `consensus.py` | `signature` chuẩn hoá đáp án để so (số làm tròn 2 chữ số, chuỗi chuẩn hoá giữ dấu, list có thứ tự, bảng so như tập dòng); `vote` chọn đáp án đạt ngưỡng, hoà ở mức cao nhất thì không chọn |
| `settings.py` | `ConsensusSettings`: `AGENT_SAMPLES` (mặc định 3), `AGENT_MIN_AGREE` (2), `AGENT_SAMPLE_TEMPERATURE` (0.6) |

Các lần sinh luân phiên hai bộ giải (pandas → SQL → pandas …); hai lần trùng đáp án thì dừng sớm.

## Đã có: `verification/` — kiểm tra bằng code

| File | Việc | Đo trên train (không gọi LLM) |
|---|---|---|
| `unanswerable.py` | Chạy **trước** khi gọi LLM: kỳ nằm hoàn toàn ngoài khoảng có dữ liệu; shop không ghi loại thông tin câu hỏi cần (tồn kho, nhập hàng, hạn dùng, giới tính / địa chỉ khách, kênh bán, hình thức thanh toán, công nợ, nhóm khách, nhân viên); câu hỏi đánh giá chủ quan | bắt 50/70 câu unanswerable, **mọi luật đúng 100%** (`scripts/check_unanswerable.py`) |
| `sanity.py` | Chạy **sau** mỗi lần sinh: tên trả về phải có trong dữ liệu (cho phép khớp trọn từ, vd. "Cao Long Minh" trong "Cao Long Minh (0321806537)"), trừ tên thứ trong tuần; phần trăm bất thường. Không qua thì lần sinh đó không được tính phiếu | **0/2930** đáp án chuẩn bị loại nhầm (`scripts/check_sanity.py`) |

Thông tin "shop có ghi gì" lấy từ `data/semantic/capabilities.py`.

## Dự kiến thêm (chưa có)

- `decide.py`: ngưỡng tin cậy hiệu chỉnh trên train (theo mức đồng thuận, nhóm câu hỏi), cần
  log của một lượt chạy thật trước.

## Công thức cần nhớ

PA = độ phủ × (2 × độ chính xác − 1), với độ phủ là tỉ lệ câu dám trả lời. Trả lời một câu chỉ có
lợi khi xác suất đúng trên 50%; muốn độ chính xác trên các câu đã trả lời cao hơn thì nâng ngưỡng,
đổi lại độ phủ giảm.

Test: `tests/modules/decision/`.
