# `modules/` — các tầng nghiệp vụ

Mỗi câu hỏi đi qua bốn tầng, cộng một tầng luật dùng chung:

```
câu hỏi + business_id + as_of_date
  │
  ├─ data/           TẦNG 1  nạp & làm sạch dữ liệu, mô tả bảng (sau này: bảng chuẩn)
  ├─ understanding/  TẦNG 2  hiểu câu hỏi: viết tắt, khoảng ngày, tên thật trong dữ liệu
  ├─ solvers/        TẦNG 3  các đường giải độc lập (hiện có: LLM viết pandas)
  └─ decision/       TẦNG 4  bỏ phiếu, quyết định trả lời / abstain
        │
        └─ domain/   dùng chung: kỳ thời gian, luật rulebook, kiểu đáp án theo đề
```

`app/` (ngoài `modules/`) ghép các tầng theo thứ tự trên. Mỗi tầng có `README.md` riêng.
Vòng lặp "LLM sinh → chạy → soát → sửa" dùng chung nằm ở `infrastructure/llm_loop/`, để mọi tầng
(kể cả tầng 1 và 2) dùng được mà không phải import `solvers/`.

## Chiều phụ thuộc

Chỉ được import tầng **thấp hơn hoặc cùng tầng**:

```
core ← infrastructure ← domain ← data ← understanding ← solvers ← decision ← app
```

- `data/` không biết `solvers/` tồn tại; `domain/` không biết gì về tầng nào phía trên.
- Các bộ giải trong `solvers/` **không import lẫn nhau**, để kết quả của chúng thật sự độc lập
  khi bỏ phiếu.
- Quy tắc được khoá bằng [tests/test_layers.py](../../../tests/test_layers.py): thêm import
  ngược tầng là test hỏng.

## Quy ước

- Mỗi package con là một mặt tiền: nơi khác chỉ import từ `datamate.modules.<tầng>.<package>`;
  danh sách công khai nằm ở `__all__` trong `__init__.py`.
- Bên trong một package thì import thẳng từ file anh em (tránh vòng import).
- Test đặt ở `tests/modules/<tầng>/<package>/`, phản chiếu cấu trúc này.
- Không tạo thư mục rỗng trước; package mới được thêm khi có code.
