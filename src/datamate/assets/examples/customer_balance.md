mô tả: Dư nợ của khách đến hết ngày D = tổng 'Nợ thêm' của đơn đặt đến D trừ tổng tiền trả nợ ('Là trả nợ') thu đến D, theo 'Khách định danh'. Đếm khách còn nợ / xếp hạng khách nợ nhiều nhất: dùng dư nợ > 0. Dùng bảng đầy đủ don_chuan và thanh_toan_chuan.

## pandas
```python
o = T["don_chuan"]
o = o[o["Khách định danh"].notna() & (o["Ngày đặt"] <= pd.Timestamp("2026-03-04"))]
p = T["thanh_toan_chuan"]
p = p[p["Là trả nợ"] & p["Khách định danh"].notna() & (p["Ngày thu"] < pd.Timestamp("2026-03-05"))]
owed = o.groupby("Khách định danh")["Nợ thêm"].sum().sub(p.groupby("Khách định danh")["Số tiền thu"].sum(), fill_value=0)
owed = owed[owed > 0]
answer = {"type": "number", "answer": int(len(owed))}
# top 3 khách nợ nhiều nhất: owed.sort_values(ascending=False).head(3); tên khách lấy từ cột 'Tên khách'
```

## sql
```sql
-- type: number
WITH no_them AS (
  SELECT "Khách định danh" AS k, SUM("Nợ thêm") AS v FROM "don_chuan"
  WHERE "Khách định danh" IS NOT NULL AND CAST("Ngày đặt" AS DATE) <= DATE '2026-03-04' GROUP BY k
), tra_no AS (
  SELECT "Khách định danh" AS k, SUM("Số tiền thu") AS v FROM "thanh_toan_chuan"
  WHERE "Là trả nợ" AND "Khách định danh" IS NOT NULL AND CAST("Ngày thu" AS DATE) <= DATE '2026-03-04' GROUP BY k
)
SELECT COUNT(*) FROM no_them LEFT JOIN tra_no USING (k)
WHERE no_them.v - COALESCE(tra_no.v, 0) > 0
```
