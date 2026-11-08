mô tả: Biến thể ghi trong tên hàng ('ly size L', 'loại M', vị...): gom MỌI mặt hàng có hậu tố đó, cộng số lượng. Tên thường kết thúc bằng '(L)' nên lọc theo hậu tố, không tìm 'size L'.

## pandas
```python
d = T["dong_hang_tinh_doanh_thu"]
d = d[P.month(2026, 3).contains(d["Ngày đặt"])]
d = d[d["Tên hàng"].astype(str).str.strip().str.endswith("(L)")]
answer = {"type": "number", "answer": int(d["Số lượng quy đổi"].sum())}
```

## sql
```sql
-- type: number
SELECT COALESCE(SUM("Số lượng quy đổi"), 0) FROM "dong_hang_tinh_doanh_thu"
WHERE CAST("Ngày đặt" AS DATE) BETWEEN DATE '2026-03-01' AND DATE '2026-03-31'
  AND trim("Tên hàng") LIKE '%(L)'
```
