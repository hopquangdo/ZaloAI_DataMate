# `data/` — TẦNG 1: dữ liệu

Biến gói dữ liệu thô của một doanh nghiệp (CSV, Excel nhiều sheet, SQLite, kèm `README.md`) thành
các bảng pandas sạch, rồi mô tả chúng cho prompt. Làm **một lần cho mỗi doanh nghiệp** và cache lại.

**Được import:** `core`, `infrastructure`, `domain`.

## Thành phần

### `ingestion/` — đọc & làm sạch

| File | Việc |
|---|---|
| `readers.py` | Đọc file thô: csv, xlsx (mỗi sheet một phần), sqlite |
| `header.py` | Dò dòng tiêu đề thật (bỏ tiêu đề báo cáo, bộ lọc phía trên), đặt tên cột |
| `grouping.py` | Điền xuống ô trống của nhóm dòng (nhiều dòng chi tiết của cùng một đơn, rulebook §8) |
| `values.py` | Parse ô bẩn: tiền (`"1tr440"`, `"396k"`, `"55.000đ"`), số lượng (`"3 chai"`), ngày |
| `columns.py` | Đặt kiểu cột: ngày → `datetime64`, số → `float`, còn lại là chuỗi |
| `business.py` | Ghép các bước trên: `load_business(dir)` → `Business` (các bảng có tên + README) |
| `cache.py` | `get_business`: cache trong bộ nhớ và trên đĩa (pickle). Khoá cache băm cả dữ liệu lẫn mã nguồn ingestion, nên sửa code làm sạch là cache cũ tự mất hiệu lực |

### `profiling/` — mô tả bảng

`describe_business` tóm tắt từng bảng (số dòng, kiểu cột, khoảng ngày, giá trị mẫu, các giá trị
của cột phân loại) để đưa vào prompt.

## `semantic/` — hiểu nghĩa của cột (gợi ý cho LLM, không đổi dữ liệu)

| File | Việc |
|---|---|
| `roles.py` | Gợi ý vai trò cột (`[gợi ý: giá vốn]`, `[gợi ý: số lượng quy về đơn vị cơ bản]`…) ghi vào mô tả bảng. So trên chữ có dấu (để "hàng" / "hãng" / "hạng" không lẫn), phân tích từ chính + từ bổ nghĩa, kiểm tra kiểu giá trị và ngữ cảnh bảng (bảng nhập hàng, bảng khách). Mơ hồ thì không gợi ý |
| `capabilities.py` | Shop ghi những loại thông tin nào (theo vai trò cột, tên cột và giá trị) và khoảng ngày của bảng giao dịch chính; dùng cho luật unanswerable |

Luật nằm ở `assets/lexicon/column_roles.tsv`, cụm từ ghép ở `column_compounds.txt`: sửa được mà
không đụng code. Không có bảng chuẩn hoá (đã cân nhắc và bỏ: tên cột quá đa dạng giữa các doanh
nghiệp, map sai một cột thì sai mọi câu của doanh nghiệp đó).

## Nguyên tắc

- Không gọi LLM ở `ingestion/` và `profiling/`.
- Làm sạch theo đúng rulebook §8 (cách ghi trong file); không đoán ý nghĩa nghiệp vụ ở đây.

Test: `tests/modules/data/`.
