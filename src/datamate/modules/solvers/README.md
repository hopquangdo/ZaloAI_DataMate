# `solvers/` — TẦNG 3: các đường giải

Mỗi bộ giải nhận câu hỏi đã phân tích cùng dữ liệu của doanh nghiệp, và trả về một đáp án ứng
viên. Các bộ giải **độc lập với nhau** (không import lẫn nhau, được khoá bằng
`tests/test_layers.py`), vì giá trị của bỏ phiếu ở tầng 4 nằm ở chỗ chúng ít mắc cùng một lỗi.

**Được import:** `core`, `infrastructure`, `domain`, `data`, `understanding`.

## Đã có: `pandas/` — LLM viết code pandas

Dùng vòng lặp chung [`infrastructure/llm_loop`](../../infrastructure/llm_loop/README.md); phần
riêng của pandas chỉ gồm engine và các check:

```
generate → execute (sandbox) → RuleCheck → [LlmReviewCheck] → finalize
```

| Thành phần | Việc |
|---|---|
| `graph.py` | `build_graph(...)`: ghép `PandasEngine` + các check vào `build_loop` |
| `engine.py` | `PandasEngine`: tách khối ```` ```python ````, chạy trong sandbox, ép về đáp án theo đề; lỗi thành `AttemptError` |
| `checks.py` | `RuleCheck` (luật rẻ, không gọi LLM) và `LlmReviewCheck` (LLM soát theo rulebook, tắt mặc định) |
| `review/` | Nội dung luật, soạn feedback, đọc kết luận của LLM review |
| `sandbox/` | Kiểm tra AST trước khi chạy (cấm import, đọc/ghi file), builtins giới hạn, thời hạn cứng |
| `toolkit.py` | Các tên code được dùng: `T` (bảng), `pd`, `np`, `P` (kỳ), `lunar`, `order_status`, `round_money`, `fold`… Tài liệu cho LLM ở `assets/prompts/toolkit.md` |
| `settings.py` | `AGENT_MAX_ATTEMPTS`, `AGENT_MAX_REPEATS`, `AGENT_LLM_REVIEW` |

**Điểm yếu đã thấy với Qwen2.5-14B:** gọi hàm không tồn tại (`P.n_days`), cố `import timedelta`
dù bị cấm, lặp cùng một lỗi qua nhiều lượt sửa. DeepSeek ít mắc hơn.

## Đã có: `sql/` — LLM viết SQL (DuckDB, chỉ đọc)

| Thành phần | Việc |
|---|---|
| `engine.py` | `SqlEngine`: tách khối ```` ```sql ````, dòng đầu `-- type: <kiểu>` (hoặc `-- unanswerable: <lý do>`); chỉ cho một câu SELECT / WITH, chặn lệnh ghi và đọc file; chạy trên DuckDB trong bộ nhớ, ngắt sau 30 giây |
| `functions.py` | Hàm nghiệp vụ trong SQL: `order_status`, `fold`, `norm`, `round_money` (cùng luật với pandas, lấy từ `domain`) |
| `graph.py` | `build_sql_graph(...)`: ghép `SqlEngine` vào `infrastructure.llm_loop` |

Prompt: `assets/prompts/sql_system.md`, `sql_repair.md`. Bảng mô tả `T["X"]` thì trong SQL viết `"X"`.

## Bỏ phiếu giữa các bộ giải

`app/pipeline.py` luân phiên các lần sinh: pandas (nhiệt độ gốc) → SQL (nhiệt độ gốc) → pandas
(nhiệt độ cao hơn) … Hai lần sinh **từ hai bộ giải khác nhau** cho cùng đáp án thì đáng tin hơn hai
lần sinh của cùng một bộ giải. Số lần sinh: `AGENT_SAMPLES`, ngưỡng đồng thuận: `AGENT_MIN_AGREE`.

## Dự kiến thêm (chưa có)

- `spec_executor/`: code tính đáp án từ đặc tả JSON. Chỉ làm nếu đo thấy pandas + SQL còn thiếu.

## Thêm một bộ giải mới

1. Tạo `solvers/<tên>/`, chỉ import từ các tầng thấp hơn. Nếu bộ giải dùng LLM viết code thì viết
   một `Engine` và cắm vào `infrastructure.llm_loop.build_loop`, không tự viết vòng lặp.
2. Trả về đáp án theo `domain.answer` (`Answer`, `coerce_answer`).
3. Đăng ký trong `app/pipeline.py`; không gọi trực tiếp bộ giải khác.

Test: `tests/modules/solvers/`.
