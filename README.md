# DataMate — Zalo AI Challenge 2026

Agent trả lời câu hỏi tiếng Việt đời thường trực tiếp trên dữ liệu bảng của doanh nghiệp nhỏ
(CSV, Excel, SQLite). Mỗi câu hỏi nhận một đáp án có kiểu (`number`, `percent`, `string`, `date`,
`boolean`, `list`, `table`), hoặc `unanswerable` khi dữ liệu không đủ, hoặc `abstain` khi không đủ
tự tin. Điểm là Penalized Accuracy (PA): đúng +1, abstain 0, sai −1, nên hệ thống ưu tiên `abstain`
hơn là đoán. Đề bài và luật chấm: [docs/DEBAI.md](docs/DEBAI.md), [docs/TASK.md](docs/TASK.md).

![Pipeline overview](reports/pipeline_llm_overview.svg)

## Nguyên tắc thiết kế

- **LLM đề xuất, code quyết định.** LLM chỉ làm phần mơ hồ (viết code, đoán vai trò cột lạ, gán nhãn
  trạng thái). Mọi đầu ra của LLM đều được code kiểm chứng; thời gian, làm tròn, định dạng đáp án và
  quyết định cuối do code làm.
- **Bảng chuẩn tắc (canonical tables).** Mỗi doanh nghiệp có bố cục bảng khác nhau, nên dữ liệu được
  quy về cùng một lược đồ (đơn, dòng hàng, thanh toán / công nợ, nhập hàng, bản đã lọc đơn tính
  doanh thu) theo **rulebook của chính tập đang chạy**. Bộ giải chỉ cần hiểu một lược đồ.
- **Hai bộ giải độc lập** (pandas và SQL/DuckDB) cùng giải một câu; chỉ trả lời khi hai đáp án từ hai
  bộ giải khác nhau trùng nhau.
- **Rulebook là dữ liệu, không hard-code.** Đặc tả định nghĩa (đơn nào tính doanh thu, mốc ca…) nằm
  trong `RuleSpec`; không có logic theo `id` câu hỏi hay `business_id`.
- **Ngăn lỗi từ cấu trúc** (bảng đã lọc cờ doanh thu, cột ca / khách định danh có sẵn) tốt hơn phát
  hiện sau. LLM không được chọn đáp án khi chưa có cách kiểm chứng: thử cho LLM làm trọng tài chọn
  giữa các đáp án bất đồng chỉ đúng 25% nên đã bỏ.

## Pipeline

```
câu hỏi + business_id + as_of_date
  ① Data Preparation (một lần / doanh nghiệp, có cache)
       nạp & làm sạch (gộp bảng theo tháng) → nhận vai trò cột theo tên + giá trị
       → LLM đề xuất vai trò cột lạ (code kiểm chứng bằng giá trị) → LLM gán nhãn trạng thái đơn lạ
       → dựng bảng chuẩn tắc theo rulebook
  ② Question Understanding (mỗi câu, bằng code)
       chuẩn hoá viết tắt/Telex → gợi ý khoảng ngày (SQL và pandas) → khớp tên trong dữ liệu
       → luật "không thể trả lời"
  ③ Solving (pandas ∥ SQL, luân phiên, tối đa AGENT_SAMPLES lần)
       LLM sinh code → chạy sandbox → check luật rẻ → LLM tự sửa (tối đa 3 lần)
  ④ Decision
       bỏ phiếu cần ≥ AGENT_MIN_AGREE đáp án trùng từ ≥ 2 bộ giải → kiểm tra hợp lý → abstain nếu không chắc
  ⑤ submission.jsonl + run_log.jsonl
```

| Tầng | Package | Việc chính |
|---|---|---|
| Data | `modules/data/` | `ingestion` (đọc, gộp bảng, đặt kiểu), `semantic` (vai trò cột, `propose.py` cho vai trò do LLM đề xuất), `canonical` (bảng chuẩn tắc, bảng đã lọc, mô tả cho prompt), `profiling` |
| Understanding | `modules/understanding/` | `normalize` (viết tắt, gợi ý thời gian, khớp tên), `examples` (few-shot cho cả pandas và SQL) |
| Solvers | `modules/solvers/` | `pandas` (sandbox + `P` kỳ thời gian), `sql` (DuckDB chỉ đọc), các check dùng chung: `view_misuse`, `threshold_days`, `empty_result` |
| Decision | `modules/decision/` | `consensus` (bỏ phiếu), `verification` (kiểm tra hợp lý, luật unanswerable) |
| Domain | `modules/domain/` | kỳ thời gian và lịch âm, `business_rules` (trạng thái, `RuleSpec`, thanh toán, khách lẻ), kiểu đáp án |

## Model và tuân thủ thể lệ

- **Model khai báo:** `Qwen2.5-Coder-14B-Instruct` (AWQ, khoảng 14,7B tham số, weights công khai),
  phục vụ qua vLLM. Không dùng embedding hay model phụ khác. Thể lệ: tổng tham số ≤ 15B, weights
  công bố trước 26/10/2026.
- **Không hard-code** đáp án, `id` câu hỏi hay `business_id`. Không dùng dữ liệu test (public hoặc
  private) để huấn luyện; chỉ dùng tập train.
- Cache và file tạm ghi ngoài thư mục dữ liệu (thư mục dữ liệu được mount chỉ đọc).

## Kết quả (trung thực)

| Tập | Kết quả | Ghi chú |
|---|---|---|
| Public leaderboard, bản v5 | **PA = 0,013** | số thật khi nộp lên cổng; dự đoán nội bộ trước đó (~0,4) đã sai |
| Train dev (150 câu), bản v7 | PA +0,68 | dev đã bị đọc lỗi nhiều lần, **không dùng để dự đoán điểm public** |
| Train holdout (60 câu), bản v7 | PA +0,65 | chỉ 3 doanh nghiệp, cùng lưu ý trên |

Độ chính xác khi trả lời trên train khoảng 89%, trên public suy ra khoảng 51%: điểm train **chưa
chuyển sang** dữ liệu mới. Nguyên nhân chưa xác định hết (xem [Việc còn lại](#việc-còn-lại)). Định
dạng file nộp đã được kiểm tra đúng đặc tả (không phải nguyên nhân).

## Cấu trúc thư mục

```
src/datamate/
├── core/              # tiện ích chữ (fold, name_key, normalize_text)
├── infrastructure/    # config, client LLM, vòng lặp LLM (llm_loop), nạp prompt, jsonl
├── assets/            # prompts/*.md, examples/*.md (few-shot), lexicon/ (từ điển vai trò cột)
├── modules/           # các tầng nghiệp vụ (mỗi tầng có README riêng, xem modules/README.md)
└── app/               # pipeline (một câu), runner (CLI), business_registry, run_log
eval/                  # chấm PA, breakdown, holdout (tách khỏi src)
tests/                 # phản chiếu src/; tests/test_layers.py khoá chiều phụ thuộc giữa các tầng
scripts/               # công cụ đo và vẽ (xem bên dưới)
reports/               # kết quả chạy, sơ đồ pipeline (.svg)
docs/                  # đề bài và thể lệ
```

Chiều phụ thuộc: `core ← infrastructure ← domain ← data ← understanding ← solvers ← decision ← app`.
Các bộ giải không import lẫn nhau (để kết quả thật sự độc lập khi bỏ phiếu).

## Cài đặt và cấu hình

Cần Python ≥ 3.10 và [uv](https://docs.astral.sh/uv/).

```bash
uv sync
cp .env.example .env      # điền LLM_BASE_URL / LLM_API_KEY / LLM_MODEL
```

| Biến | Mặc định | Ý nghĩa |
|---|---|---|
| `LLM_BASE_URL` | `http://localhost:8000/v1` | API tương thích OpenAI (vLLM local) |
| `LLM_API_KEY` | `EMPTY` | khoá API |
| `LLM_MODEL` | *(bắt buộc)* | tên model được phục vụ |
| `LLM_MAX_TOKENS` | `4096` | số token tối đa model sinh ra |
| `AGENT_MAX_ATTEMPTS` | `4` | 1 lần sinh + tối đa 3 lần sửa code |
| `AGENT_SAMPLES` | `4` | số lần sinh tối đa mỗi câu (luân phiên pandas, SQL) |
| `AGENT_MIN_AGREE` | `2` | số lần sinh phải trùng đáp án mới trả lời |
| `AGENT_SAMPLE_TEMPERATURE` | `0.6` | nhiệt độ cho lần sinh thứ 2 trở đi |
| `AGENT_LLM_REVIEW` | `false` | bật bước LLM review (chưa đo được lợi ích) |

**Server LLM.** Prompt dài (rulebook, mô tả bảng, few-shot): context tối thiểu **32k token**
(đang dùng 49k với `--max-model-len 49152`, kéo dài bằng YaRN `factor=2.0`). Đặt
`VLLM_ALLOW_LONG_MAX_MODEL_LEN=1` khi kéo dài context.

## Chạy

```bash
# thử 50 câu ngẫu nhiên của train
uv run python -m datamate dataset/train/train --limit 50 --workers 6

# cả tập public, ghi nối tiếp (dừng giữa chừng vẫn giữ kết quả; --resume để chạy tiếp)
uv run python -m datamate dataset/public_test/public_test --out reports/submission.jsonl --resume

# chỉ một bộ giải, hoặc chỉ vài câu / vài doanh nghiệp
uv run python -m datamate dataset/train/train --solvers sql --business biz_101 biz_102
uv run python -m datamate dataset/train/train --ids q_0000abc q_0000def
```

Thư mục tập dữ liệu có `questions.jsonl`, `data/<business_id>/`, `rulebook.md`, `calendar.csv` (train
có thêm `answers.jsonl`). Đầu ra: `--out` (`submission.jsonl`) và `--log` (`run_log.jsonl`: các lần
sinh, nguồn bộ giải, vết từng bước, token, thời gian, lỗi). Lỗi API chỉ bỏ lần sinh đó; lỗi chương
trình ở một câu thì câu đó abstain và có traceback trong log (`--strict` để dừng ngay khi phát triển).

## Đánh giá và công cụ

```bash
# chấm PA trên train (có đáp án)
uv run python -m eval reports/submission.jsonl dataset/train/train/answers.jsonl --only-answered
uv run python -m eval.breakdown reports/run_log.jsonl dataset/train/train/answers.jsonl

# kiểm tra file nộp đúng đặc tả (đủ id, không trùng, đúng kiểu và định dạng)
uv run python scripts/validate_submission.py reports/submission.jsonl dataset/public_test/public_test

# bảng chuẩn tắc đúng đến đâu (đối chiếu câu đơn giản với đáp án train, không gọi LLM)
uv run python scripts/check_canonical.py

# LLM đề xuất vai trò cột: độ phủ và độ khớp, có / không đổi tên cột lạ (gọi LLM)
uv run python scripts/check_roles.py --only biz_101 biz_102

# audit file nộp: định dạng nghiêm ngặt và đối chiếu câu đơn giản với bảng chuẩn theo doanh nghiệp
uv run python scripts/audit_submission.py reports/submission.jsonl dataset/public_test/public_test

# vẽ lại sơ đồ pipeline (reports/*.svg)
uv run python scripts/_draw_pipeline_llm.py
```

Few-shot trong `assets/examples/` được sinh từ `scripts/_write_examples.py` (sửa script rồi chạy lại,
không sửa tay file `.md`).

## Docker (bản nộp cuối)

Thể lệ: chấm bằng **Docker image chạy offline** (không mạng, không API ngoài), mount tập test tại
`/data` (chỉ đọc), thu `/result/submission.jsonl`; toàn bộ tập private (~500 câu) trong **6 giờ**
trên 2 × RTX 5090 (CUDA ≥ 12.8); hai lần chạy phải khớp (|ΔPA| ≤ 0,03).

`Dockerfile` hiện tại **chưa đạt**: chỉ đóng gói agent Python, gọi LLM qua `LLM_BASE_URL`. Bản nộp
cuối cần thêm: vLLM + trọng số model trong image (không tải lúc chạy), khởi động server LLM bên
trong container trước khi chạy agent, `temperature` thấp và `seed` cố định cho lần chạy chính thức,
và ghi từng câu ngay khi xong để hết giờ vẫn giữ phần đã làm.

```bash
docker build -t datamate .
docker run --rm -v "$PWD/dataset/public_test/public_test:/data:ro" -v "$PWD/result:/result" datamate
```

## Kiểm thử

```bash
uv run pytest -q            # test cần dữ liệu tự bỏ qua nếu thiếu dataset/
uv run ruff check src eval tests
```

Test của `app/` dùng LLM giả có kịch bản nên chạy không cần mạng hay API key.

## Việc còn lại

- **Điểm public rất thấp (0,013).** Cần tìm doanh nghiệp / nhóm câu sai hệ thống (chạy
  `audit_submission.py`), đặc biệt các loại hình mới của rulebook public (mẹ và bé, sửa xe, điện
  thoại) mà bảng chuẩn tắc chưa có cột riêng.
- **Bản nộp Docker offline** (xem trên) chưa làm; chưa đo thời gian chạy trên phần cứng tham chiếu.
- **Bất đồng giữa hai bộ giải** là chỗ mất điểm lớn nhất (khoảng 24% câu public); thử re-solve rồi
  bỏ phiếu bằng execution thay vì để LLM chọn.
- **Bước "LLM làm rõ câu hỏi"** (dạng đáp án, bảng cần dùng) và **format guard** mới ở dạng đề xuất,
  chưa cài đặt.
- Chưa có bảng chuẩn cho tồn kho (xếp theo đơn vị lớn / nhỏ) và dư nợ tổng quát hơn.
- Bộ test đổi tên cột (`check_roles.py`) mới là kịch bản nhân tạo; cần thêm doanh nghiệp holdout thật.
