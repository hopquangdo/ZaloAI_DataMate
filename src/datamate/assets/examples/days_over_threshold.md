mô tả: Đếm số NGÀY đạt ngưỡng doanh thu: cộng doanh thu theo từng ngày trước, rồi mới so với ngưỡng (không so từng đơn).

## pandas
```python
d = T["don_tinh_doanh_thu"]
d = d[P.month(2026, 3).contains(d["Ngày đặt"])]
by_day = d.groupby(d["Ngày đặt"].dt.date)["Doanh thu đơn"].sum()
answer = {"type": "number", "answer": int((by_day >= 10_000_000).sum())}
```

## sql
```sql
-- type: number
SELECT COUNT(*) FROM (
  SELECT CAST("Ngày đặt" AS DATE) AS ngay FROM "don_tinh_doanh_thu"
  WHERE CAST("Ngày đặt" AS DATE) BETWEEN DATE '2026-03-01' AND DATE '2026-03-31'
  GROUP BY ngay HAVING SUM("Doanh thu đơn") >= 10000000
)
```
