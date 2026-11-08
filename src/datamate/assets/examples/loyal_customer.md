mô tả: Khách trung thành nhất = khách có NHIỀU NGÀY CÓ MUA nhất trong kỳ (đếm ngày khác nhau, không đếm đơn).

## pandas
```python
d = T["don_tinh_doanh_thu"]
d = d[P.month(2026, 3).contains(d["Ngày đặt"]) & d["Khách định danh"].notna()]
days = d.groupby("Khách định danh")["Ngày đặt"].apply(lambda s: s.dt.date.nunique())
best = days.sort_values(ascending=False).index[0]
answer = {"type": "string", "answer": d.loc[d["Khách định danh"] == best, "Tên khách"].iloc[0]}
```

## sql
```sql
-- type: string
SELECT any_value("Tên khách") FROM "don_tinh_doanh_thu"
WHERE "Khách định danh" IS NOT NULL
  AND CAST("Ngày đặt" AS DATE) BETWEEN DATE '2026-03-01' AND DATE '2026-03-31'
GROUP BY "Khách định danh"
ORDER BY COUNT(DISTINCT CAST("Ngày đặt" AS DATE)) DESC
LIMIT 1
```
