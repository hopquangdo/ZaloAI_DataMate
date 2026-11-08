mô tả: Đếm đơn bị huỷ: đếm theo trạng thái chuẩn 'huy' trên bảng đơn, không lọc cờ tính doanh thu.

## pandas
```python
d = T["don_chuan"]
d = d[(d["Trạng thái chuẩn"] == "huy") & P.month(2026, 3).contains(d["Ngày đặt"])]
answer = {"type": "number", "answer": int(len(d))}
```

## sql
```sql
-- type: number
SELECT COUNT(*) FROM "don_chuan"
WHERE "Trạng thái chuẩn" = 'huy'
  AND CAST("Ngày đặt" AS DATE) BETWEEN DATE '2026-03-01' AND DATE '2026-03-31'
```
