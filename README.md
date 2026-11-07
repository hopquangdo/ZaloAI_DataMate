# DataMate — Zalo AI Challenge 2026

Agent trả lời câu hỏi tiếng Việt đời thường trực tiếp trên dữ liệu bảng của doanh nghiệp nhỏ
(CSV, Excel, SQLite). Với mỗi câu hỏi, agent trả về một đáp án có kiểu (`number`, `percent`,
`string`, `date`, `boolean`, `list`, `table`), hoặc `unanswerable` khi dữ liệu không đủ, hoặc
`abstain` khi không đủ tự tin. Đề bài và luật chấm: [docs/DEBAI.md](docs/DEBAI.md),
[docs/TASK.md](docs/TASK.md).

Điểm chấm là Penalized Accuracy: đúng +1, abstain 0, sai −1. Vì vậy hệ thống chỉ trả lời khi đủ
tự tin và ưu tiên `abstain` hơn là đoán.

## Cách hoạt động

```
câu hỏi + business_id + as_of_date
  → nạp & làm sạch bảng của doanh nghiệp (cache theo doanh nghiệp)
  → mô tả bảng (profiling) + gợi ý từ câu hỏi (viết tắt, khoảng ngày, tên thật trong dữ liệu)
  → LLM viết code pandas → chạy trong sandbox → kiểm tra luật → ép về đúng kiểu đáp án
  → lặp tối đa AGENT_SAMPLES lần độc lập; chỉ trả lời nếu ≥ AGENT_MIN_AGREE lần trùng đáp án
  → submission.jsonl
```

LLM chỉ viết code; thời gian, làm tròn, phân loại trạng thái đơn, định dạng đáp án đều do code
quyết định.

## Cấu trúc thư mục

```
src/datamate/
├── core/                  # tiện ích chữ thuần (fold, normalize_text, shorten)
├── infrastructure/        # config LLM, client LLM, đọc đầu ra LLM, nạp prompt, jsonl
├── assets/prompts/        # system.md, user.md, repair.md, review.md, toolkit.md
├── modules/               # các tầng nghiệp vụ — xem modules/README.md
│   ├── domain/            # dùng chung: periods (kỳ thời gian, lịch âm), business_rules, answer (kiểu đáp án)
│   ├── data/              # TẦNG 1: ingestion (đọc & làm sạch, cache), profiling (mô tả bảng)
│   ├── understanding/     # TẦNG 2: normalize (viết tắt, gợi ý thời gian, khớp tên)
│   ├── solvers/           # TẦNG 3: pandas (LLM viết code: đồ thị LangGraph, sandbox, toolkit)
│   └── decision/          # TẦNG 4: consensus (bỏ phiếu giữa các lần sinh)
└── app/                   # ghép các tầng: pipeline (một câu), runner (CLI), question, run_log, business_registry, knowledge
eval/                      # chấm điểm PA — tách khỏi src, không đóng gói vào bản nộp
tests/                     # phản chiếu src/; tests/test_layers.py khoá chiều phụ thuộc giữa các tầng
scripts/  docs/
```

Chiều phụ thuộc: `core ← infrastructure ← domain ← data ← understanding ← solvers ← decision ← app`
(chỉ import tầng thấp hơn; các bộ giải không import lẫn nhau). Mỗi tầng có `README.md` riêng.

## Cài đặt

Cần Python ≥ 3.10 và [uv](https://docs.astral.sh/uv/).

```bash
uv sync                      # cài thư viện, gồm nhóm dev
cp .env.example .env         # rồi điền LLM_BASE_URL / LLM_API_KEY / LLM_MODEL
```

`.env` và mọi file `.env.*` (trừ `.env.example`) đã nằm trong `.gitignore`, đừng commit khoá API.

### Cấu hình

| Biến | Mặc định | Ý nghĩa |
|---|---|---|
| `LLM_BASE_URL` | `http://localhost:8000/v1` | API tương thích OpenAI (vLLM, OpenRouter...) |
| `LLM_API_KEY` | `EMPTY` | Khoá API |
| `LLM_MODEL` | *(bắt buộc)* | Tên model |
| `LLM_MAX_TOKENS` | `4096` | Số token tối đa model sinh ra |
| `AGENT_MAX_ATTEMPTS` | `4` | 1 lần sinh + tối đa 3 lần sửa code |
| `AGENT_SAMPLES` | `3` | Số lần sinh độc lập tối đa cho mỗi câu |
| `AGENT_MIN_AGREE` | `2` | Số lần sinh phải trùng đáp án mới trả lời |
| `AGENT_SAMPLE_TEMPERATURE` | `0.6` | Nhiệt độ cho lần sinh thứ 2 trở đi |
| `AGENT_LLM_REVIEW` | `false` | Bật bước LLM review |

Đặt `AGENT_SAMPLES=1 AGENT_MIN_AGREE=1` để chạy một lần sinh mỗi câu (nhanh hơn, không có bỏ phiếu).

**Lưu ý về model.** Đề giới hạn tổng tham số các model dưới 16B. Model đang cấu hình để thử là
`qwen2.5-14b` (khoảng 14.7B). Prompt (rulebook + mô tả bảng) khá dài: nên đặt context của server
LLM tối thiểu **32k token**, 16k không đủ cho các doanh nghiệp lớn.

## Chạy

```bash
# chạy thử 50 câu ngẫu nhiên của tập train
uv run python -m datamate dataset/train/train --limit 50 --workers 8

# chạy cả tập, ghi nối tiếp để dừng giữa chừng vẫn giữ kết quả; --resume để chạy tiếp
uv run python -m datamate dataset/train/train --out reports/submission.jsonl --resume
```

**Xử lý lỗi.** Lỗi gọi API chỉ làm lần sinh đó bị bỏ qua (log ghi `error_kind: "api"`). Lỗi chương
trình ở một câu thì câu đó abstain, log ghi `error_kind: "bug"` kèm traceback, và cuối lượt có dòng
cảnh báo tổng số câu lỗi. Thêm `--strict` khi phát triển để dừng ngay ở lỗi chương trình đầu tiên.

Thư mục dữ liệu của một tập phải có `questions.jsonl`, `data/<business_id>/`, `rulebook.md`,
`calendar.csv` (tập `train` có thêm `answers.jsonl`). Kết quả: `--out` (mặc định
`reports/submission.jsonl`) và `--log` (mặc định `reports/run_log.jsonl`, có nhật ký từng lượt
sinh, số token, thời gian).

### Chấm điểm

```bash
uv run python -m eval reports/submission.jsonl dataset/train/train/answers.jsonl --only-answered
```

`--only-answered` chỉ chấm các id có trong file nộp (dùng khi chạy thử một phần tập).

## Công cụ đo (không gọi LLM trừ khi ghi rõ)

```bash
uv run python -m eval reports/submission.jsonl dataset/train/train/answers.jsonl --only-answered
uv run python -m eval.breakdown reports/run_log.jsonl dataset/train/train/answers.jsonl  # theo nguồn đáp án, doanh nghiệp
uv run python -m eval.holdout dataset/train/train          # chia doanh nghiệp dev / holdout
uv run python scripts/check_unanswerable.py dataset/train/train   # độ chính xác luật unanswerable
uv run python scripts/check_sanity.py dataset/train/train         # kiểm tra hợp lý không loại nhầm đáp án chuẩn
uv run python scripts/validate_submission.py reports/submission.jsonl dataset/public_test/public_test --fix result/submission.jsonl
```

Runner dừng lượt chạy khi 20 câu liên tiếp lỗi API (hết tiền, server sập); các câu đó không được
ghi, chạy lại với `--resume`.

## Docker

```bash
docker build -t datamate .

docker run --rm \
  -e LLM_BASE_URL=http://host.docker.internal:8000/v1 -e LLM_API_KEY=EMPTY -e LLM_MODEL=qwen2.5-14b \
  -v "$PWD/dataset/public_test/public_test:/data:ro" \
  -v "$PWD/result:/result" \
  datamate
```

Mặc định image chạy `python -m datamate /data --out /result/submission.jsonl`. Đổi tham số bằng
cách truyền sau tên image, ví dụ `datamate /data --limit 5 --workers 2`.

> **Chưa kiểm chứng với thể lệ.** Các đường dẫn `/data`, `/result`, việc image gọi LLM qua mạng
> và việc image không kèm trọng số model là *giả định*. Trang thi
> (https://challenge.zalo.ai/portal/datamate) là trang tải bằng JavaScript nên chưa đọc được nội
> dung. Hãy đối chiếu với hướng dẫn nộp bài chính thức (đường dẫn vào/ra, có mạng hay GPU khi
> chấm không, cách đóng gói model) rồi chỉnh `Dockerfile` cho khớp.

## Kiểm thử và chất lượng

```bash
uv run pytest -q             # test đơn vị; các test cần dữ liệu tự bỏ qua nếu thiếu dataset/
uv run ruff check src eval tests
```

Các test của `app/` dùng LLM giả có kịch bản nên chạy không cần mạng hay API key.

## Trạng thái

- Pipeline chạy hoàn chỉnh từ nạp dữ liệu đến ghi `submission.jsonl`; test đơn vị đều pass.
- Chưa đo điểm trên model hợp lệ (< 16B) với context đủ lớn: các lần đo đã làm dùng một model
  không hợp lệ (DeepSeek qua OpenRouter) hoặc bị lỗi context/hạ tầng, nên **chưa có điểm đáng tin**.
- Chưa đo được lợi ích của bỏ phiếu nhiều lần sinh (`AGENT_SAMPLES`) trên dữ liệu thật.
- Chưa chạy đánh giá trên `public_test` (không có đáp án để chấm cục bộ).
