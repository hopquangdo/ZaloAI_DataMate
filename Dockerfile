# DataMate agent — Zalo AI Challenge 2026
#
# Build : docker build -t datamate .
# Run   : docker run --rm \
#             -e LLM_BASE_URL=... -e LLM_API_KEY=... -e LLM_MODEL=... \
#             -v <thư mục có questions.jsonl, data/, rulebook.md, calendar.csv>:/data:ro \
#             -v <thư mục kết quả>:/result \
#             datamate
#
# Đường dẫn /data và /result là GIẢ ĐỊNH (theo docstring của runner), chưa đối chiếu với thể lệ
# nộp bài chính thức. Đổi ở CMD hoặc truyền tham số khác khi `docker run`.
FROM python:3.12-slim

COPY --from=ghcr.io/astral-sh/uv:0.5 /uv /usr/local/bin/uv

ENV UV_COMPILE_BYTECODE=1 \
    UV_LINK_MODE=copy \
    PYTHONUNBUFFERED=1 \
    PYTHONUTF8=1

WORKDIR /app

# Cài thư viện trước (tận dụng cache layer khi chỉ sửa code)
COPY pyproject.toml uv.lock ./
RUN uv sync --frozen --no-dev --no-install-project

COPY src ./src
RUN uv sync --frozen --no-dev

ENV PATH="/app/.venv/bin:$PATH"

# Cache doanh nghiệp đã nạp nằm ngoài /app để không phình layer
ENTRYPOINT ["python", "-m", "datamate"]
CMD ["/data", "--out", "/result/submission.jsonl", "--log", "/result/run_log.jsonl", "--cache-dir", "/tmp/datamate-cache", "--workers", "8"]
