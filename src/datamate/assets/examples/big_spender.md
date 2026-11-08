mô tả: Khách sộp nhất = giá trị TRUNG BÌNH một đơn cao nhất, chỉ xét khách có từ 3 đơn trở lên trong kỳ. Khách hay đổi ý = nhiều đơn huỷ nhất (dùng bảng đầy đủ don_chuan).

## pandas
```python
d = T["don_tinh_doanh_thu"]
d = d[P.month(2026, 3).contains(d["Ngày đặt"]) & d["Khách định danh"].notna()]
g = d.groupby("Khách định danh").agg(ten=("Tên khách", "first"), so_don=("Mã đơn", "count"), tb=("Doanh thu đơn", "mean"))
g = g[g["so_don"] >= 3].sort_values("tb", ascending=False)
answer = {"type": "string", "answer": g["ten"].iloc[0]}
```

## sql
```sql
-- type: string
SELECT any_value("Tên khách") FROM "don_tinh_doanh_thu"
WHERE "Khách định danh" IS NOT NULL
  AND CAST("Ngày đặt" AS DATE) BETWEEN DATE '2026-03-01' AND DATE '2026-03-31'
GROUP BY "Khách định danh"
HAVING COUNT(*) >= 3
ORDER BY AVG("Doanh thu đơn") DESC
LIMIT 1
```
