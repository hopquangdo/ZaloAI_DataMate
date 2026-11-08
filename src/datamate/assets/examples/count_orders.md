mô tả: Đếm số đơn bán được: đếm dòng của bảng đơn đã lọc (don_tinh_doanh_thu), không đếm dòng hàng.

## pandas
```python
d = T["don_tinh_doanh_thu"]
d = d[P.month(2026, 3).contains(d["Ngày đặt"])]
answer = {"type": "number", "answer": int(len(d))}
```

## sql
```sql
-- type: number
SELECT COUNT(*) FROM "don_tinh_doanh_thu"
WHERE CAST("Ngày đặt" AS DATE) BETWEEN DATE '2026-03-01' AND DATE '2026-03-31'
```
