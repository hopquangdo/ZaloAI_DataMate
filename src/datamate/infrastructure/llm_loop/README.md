# `infrastructure/llm_loop/` — vòng lặp LLM dùng chung

Vòng "LLM sinh → chạy → soát → sửa theo feedback" mà nhiều tầng cần: bộ giải pandas, bộ giải SQL
(dự kiến), điền đặc tả JSON (dự kiến), gợi ý map cột (dự kiến). Đặt ở `infrastructure` vì không
chứa nghiệp vụ, nên **mọi tầng đều import được** mà không phá chiều phụ thuộc.

```
generate ─→ execute ─→ check_1 ─→ … ─→ check_n ─→ finalize ─→ END
   ↑______ còn feedback và còn lượt __________________|
```

## Cắm một bộ giải vào

```python
from datamate.infrastructure.llm_loop import AttemptError, LoopSettings, build_loop, initial_state

class SqlEngine:
    language = "sql"                      # LLM phải viết khối ```sql```
    def extract(self, reply): ...         # lấy code từ câu trả lời, None nếu không thấy
    def run(self, code): ...              # trả kết quả; hỏng thì raise AttemptError("feedback")
    def describe(self, candidate): ...    # kết quả dạng JSON để ghi nhật ký

loop = build_loop(llm, SqlEngine(), checks=[...], settings=LoopSettings(), fallback=ABSTAIN)
state = loop.invoke(initial_state(question, messages))
state["answer"], state["attempts"], state["tokens"], state["trace"]
```

## Check

Một `Check` có `name`, `kind` và `__call__(state) -> CheckResult | None`.

| `kind` | Ý nghĩa | Hết lượt mà vẫn bị bác |
|---|---|---|
| `"rule"` | Luật rẻ, chỉ nhắc nhở; nên trả `names` để mỗi luật bắn một lần (`state["warned"]`) | Giữ kết quả hợp lệ gần nhất |
| `"llm"` | Một bên soát độc lập (tốn thêm lượt gọi) | Trả `fallback` (abstain) |

`CheckResult(feedback=None, tokens=..., trace=...)` nghĩa là **đạt** nhưng vẫn cộng token và ghi
nhật ký (dùng cho check gọi LLM).

## Cấu hình (`LoopSettings`)

| Trường | Mặc định | Ý nghĩa |
|---|---|---|
| `max_attempts` | 4 | 1 lần sinh + tối đa 3 lần sửa |
| `max_repeats` | 2 | Cùng một lỗi liên tiếp bao nhiêu lượt thì dừng (0 = không dừng sớm). Chặn trường hợp model lặp một lỗi mãi, như Qwen từng tốn 118k token cho một câu |
| `repair_prompt` | `"repair"` | Tên prompt sửa lỗi trong `assets/prompts/` |

Trạng thái chung là `LoopState`; `trace` chỉ chứa kiểu JSON thuần nên ghi thẳng vào run log.

Test: `tests/infrastructure/test_llm_loop.py` (dùng engine giả, không phụ thuộc pandas hay đáp án).
