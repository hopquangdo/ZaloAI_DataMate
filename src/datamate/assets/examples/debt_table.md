mô tả: Bảng khách nợ nhiều nhất đến hết ngày D: cột đặt tên không dấu dạng snake_case (khach_hang, so_tien_no); ô số là number. Dư nợ = nợ thêm − trả nợ theo 'Khách định danh'.

## pandas
```python
o = T["don_chuan"]
o = o[o["Khách định danh"].notna() & (o["Ngày đặt"] <= pd.Timestamp("2026-03-04"))]
p = T["thanh_toan_chuan"]
p = p[p["Là trả nợ"] & p["Khách định danh"].notna() & (p["Ngày thu"] < pd.Timestamp("2026-03-05"))]
owed = o.groupby("Khách định danh")["Nợ thêm"].sum().sub(p.groupby("Khách định danh")["Số tiền thu"].sum(), fill_value=0)
names = o.drop_duplicates("Khách định danh").set_index("Khách định danh")["Tên khách"]
top = owed.sort_values(ascending=False).head(3)
rows = [[names[k], round_money(v)] for k, v in top.items()]
answer = {"type": "table", "answer": {"columns": ["khach_hang", "so_tien_no"], "rows": rows}}
```

## sql
```sql
-- type: table
WITH no_them AS (
  SELECT "Khách định danh" AS k, any_value("Tên khách") AS ten, SUM("Nợ thêm") AS v FROM "don_chuan"
  WHERE "Khách định danh" IS NOT NULL AND CAST("Ngày đặt" AS DATE) <= DATE '2026-03-04' GROUP BY k
), tra_no AS (
  SELECT "Khách định danh" AS k, SUM("Số tiền thu") AS v FROM "thanh_toan_chuan"
  WHERE "Là trả nợ" AND "Khách định danh" IS NOT NULL AND CAST("Ngày thu" AS DATE) <= DATE '2026-03-04' GROUP BY k
)
SELECT ten AS khach_hang, round_money(no_them.v - COALESCE(tra_no.v, 0)) AS so_tien_no
FROM no_them LEFT JOIN tra_no USING (k)
ORDER BY so_tien_no DESC LIMIT 3
```
