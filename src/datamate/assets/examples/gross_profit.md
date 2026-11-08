mô tả: Lãi gộp = tổng cột 'Lãi gộp dòng' (thành tiền − số lượng × giá vốn ghi trên dòng) của bảng dòng hàng đã lọc; không tính lại giá vốn từ phiếu nhập.

## pandas
```python
d = T["dong_hang_tinh_doanh_thu"]
d = d[P.month(2026, 3).contains(d["Ngày đặt"])]
answer = {"type": "number", "answer": round_money(d["Lãi gộp dòng"].sum())}
```

## sql
```sql
-- type: number
SELECT round_money(SUM("Lãi gộp dòng")) FROM "dong_hang_tinh_doanh_thu"
WHERE CAST("Ngày đặt" AS DATE) BETWEEN DATE '2026-03-01' AND DATE '2026-03-31'
```
