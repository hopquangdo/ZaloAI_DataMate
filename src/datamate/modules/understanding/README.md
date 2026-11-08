# `understanding/` — TẦNG 2: hiểu câu hỏi

Chuyển câu hỏi tiếng Việt đời thường (viết tắt, không dấu, gõ sai) thành thông tin chính xác mà
bộ giải dùng được: câu viết lại đầy đủ, khoảng ngày cụ thể, tên thật có trong dữ liệu.

**Được import:** `core`, `infrastructure`, `domain`, `data`.

## Thành phần

### `normalize/` — phân tích bằng code (không gọi LLM)

| File | Việc |
|---|---|
| `normalize.py` | Gộp khoảng trắng, mở rộng viết tắt an toàn (`sp` → sản phẩm, `dthu` → doanh thu). Không đụng từ mơ hồ như `k` (vì `50k` là năm mươi nghìn) |
| `time_hints.py` | Quy cách nói thời gian thành khoảng ngày theo rulebook §2 (hôm qua, tuần rồi, tháng này so với tháng trước, tháng M không ghi năm, quý, N ngày gần nhất) |
| `entities.py` | `EntityIndex`: chỉ mục tên hàng/khách/nhóm của doanh nghiệp theo dạng không dấu; tìm cụm dài nhất trong câu hỏi trùng với giá trị thật |
| `understanding.py` | `understand(...)` gộp ba phần trên thành khối gợi ý đưa vào prompt |

Kết quả là **gợi ý**, không thay câu hỏi gốc: câu gốc vẫn được gửi nguyên cho LLM, nên mở rộng
viết tắt sai cũng không làm hỏng câu hỏi.

Đã có thêm:
- `telex.py`: giải mã Telex sót (`dduwowcj` → được, `toongr` → tổng). Chỉ giải khi chắc: âm tiết
  tiếng Việt không kết thúc bằng s/f/r/x/j, kết quả phải là âm tiết hợp lệ; bỏ qua từ viết hoa và
  từ ngoại ngắn (`Max`, `box`, `gas`).
- Từ điển viết tắt ở `assets/lexicon/abbreviations.tsv`, rút từ câu hỏi train + public_test; đã bỏ
  các viết tắt mơ hồ (`k`, `z`, `duoc`, `dt`).
- `entities.py` khớp **gần đúng** tên gõ sai nhẹ ("panadol exta…" ≈ "Panadol Extra…"); xét cụm dài
  trước để một từ đơn như "viên" không chặn mất cả tên hàng.

## Dự kiến thêm (chưa có)

- `retrieval/`: ví dụ few-shot đã kiểm đúng từ train (cần chạy model trên train trước).
- `spec/`: LLM điền đặc tả JSON. Chỉ làm nếu đo thấy cần.

## Đã thử và không dùng

Model sửa chính tả `nrl-ai/vn-spell-correction-base` (ViT5, 226M tham số): khôi phục dấu tốt ở câu
thường nhưng sửa sai các viết tắt nghiệp vụ (`dthu` → "dự thi", `hnay` → "máy") và đổi nghĩa từ
đúng ("giá nhập" → "gia nhập"). Không xử lý được Telex. Xem lịch sử phân tích trước khi thử lại.

Test: `tests/modules/understanding/`.

## examples/ — ví dụ mẫu (few-shot)

Chọn tối đa 3 ví dụ tổng quát (`assets/examples/*.md`) hợp câu hỏi theo biểu thức `triggers:`, mỗi ví dụ có bản pandas và bản SQL. `app/pipeline.py` chèn bản đúng ngôn ngữ của bộ giải vào cuối prompt người dùng. Ví dụ chỉ minh hoạ cấu trúc phép tính (đếm theo mã đơn khác nhau, tỉ lệ huỷ, xếp hạng...), không dùng tên cột hay số của doanh nghiệp nào. Thêm ví dụ mới = thêm một file `.md`.
