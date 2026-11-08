mô tả: Xếp hạng hàng bán chạy theo SỐ LƯỢNG QUY ĐỔI (không theo số dòng hay số tiền), bỏ đơn huỷ/trả.

## pandas
```python
d = T["dong_hang_tinh_doanh_thu"]
d = d[P.month(2026, 3).contains(d["Ngày đặt"])]
top = d.groupby("Tên hàng")["Số lượng quy đổi"].sum().sort_values(ascending=False).head(3)
answer = {"type": "list", "answer": list(top.index)}
```

## sql
```sql
-- type: list
SELECT "Tên hàng" FROM "dong_hang_tinh_doanh_thu"
WHERE CAST("Ngày đặt" AS DATE) BETWEEN DATE '2026-03-01' AND DATE '2026-03-31'
GROUP BY "Tên hàng"
ORDER BY SUM("Số lượng quy đổi") DESC
LIMIT 3
```
