mô tả: Xếp hạng khách: nhóm theo 'Khách định danh' (đã loại khách lẻ), trả 'Tên khách'. Khách mua nhiều tiền nhất xếp theo doanh thu.

## pandas
```python
d = T["don_tinh_doanh_thu"]
d = d[P.month(2026, 3).contains(d["Ngày đặt"]) & d["Khách định danh"].notna()]
rank = d.groupby("Khách định danh").agg(ten=("Tên khách", "first"), tien=("Doanh thu đơn", "sum"))
top = rank.sort_values("tien", ascending=False).head(3)
answer = {"type": "list", "answer": list(top["ten"])}
```

## sql
```sql
-- type: list
SELECT any_value("Tên khách") FROM "don_tinh_doanh_thu"
WHERE "Khách định danh" IS NOT NULL
  AND CAST("Ngày đặt" AS DATE) BETWEEN DATE '2026-03-01' AND DATE '2026-03-31'
GROUP BY "Khách định danh"
ORDER BY SUM("Doanh thu đơn") DESC
LIMIT 3
```
