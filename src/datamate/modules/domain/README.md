# `domain/` — luật nghiệp vụ dùng chung

Những gì **mọi tầng** cần và chỉ phụ thuộc vào đề bài (rulebook, luật chấm), không phụ thuộc vào
dữ liệu cụ thể của doanh nghiệp nào. Ví dụ: tầng dữ liệu dùng phân loại trạng thái đơn để dựng
bảng, tầng hiểu câu hỏi dùng kỳ thời gian để gợi ý khoảng ngày, bộ giải dùng làm tròn tiền.

**Được import:** `core`, `infrastructure`. **Không import** tầng nào khác trong `modules/`.

## Thành phần

| Package | Việc | Theo |
|---|---|---|
| `periods/` | Quy đổi cách nói thời gian thành khoảng ngày đóng hai đầu (`Period`): tháng này, tuần rồi, N ngày gần nhất, quý, cùng kỳ… `LunarCalendar` đọc `calendar.csv`, tính dịp Tết | rulebook §2 |
| `business_rules/` | `round_money`, `pct`, `pct_change`; `classify_status` / `order_status` phân loại trạng thái đơn viết tự do thành `hoan_thanh`, `huy`, `tra_hang`, `dang_giao`, `khac` | rulebook §1, §3, §6 |
| `answer/` | Kiểu đáp án theo đề (`Answer`, `AnswerType`, `Table`, `ABSTAIN`) và `coerce_answer` ép kết quả về đúng format, sai thì `FormatError` | docs/TASK.md §6.1, rulebook §9 |

## Dự kiến thêm (chưa có)

- `business_rules/units.py`: quy đổi về đơn vị cơ bản (hộp → viên…).
- `business_rules/ranking.py`: xếp hạng giảm dần, đồng hạng theo mã tăng dần (rulebook §3).

## Nguyên tắc

- Hàm thuần, không đọc file, không gọi LLM (trừ `LunarCalendar.load` đọc `calendar.csv`).
- Mọi luật trong rulebook mà code có thể quyết định thì đặt ở đây, để LLM không phải tự nhớ.

Test: `tests/modules/domain/`.
