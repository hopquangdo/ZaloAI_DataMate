mô tả: So với CÙNG KỲ tháng trước: kỳ này là từ đầu tháng đến hết hôm nay; kỳ trước là tháng trước có cùng số ngày (dùng khoảng ngày đã cho trong gợi ý thời gian). Phần trăm thay đổi = (kỳ này − kỳ trước) / kỳ trước.

## pandas
```python
d = T["don_tinh_doanh_thu"]
now = d.loc[P.this_month(today).contains(d["Ngày đặt"]), "Doanh thu đơn"].sum()
before = d.loc[P.last_month_same_days(today).contains(d["Ngày đặt"]), "Doanh thu đơn"].sum()
answer = {"type": "percent", "answer": pct_change(now, before)}
```

## sql
```sql
-- type: percent
-- (thay hai khoảng ngày bằng khoảng ngày trong gợi ý: tháng này đến hết hôm nay; tháng trước cùng số ngày)
SELECT ROUND(100.0 * (now - before) / before, 2) FROM (
  SELECT
    SUM("Doanh thu đơn") FILTER (WHERE CAST("Ngày đặt" AS DATE) BETWEEN DATE '2026-03-01' AND DATE '2026-03-04') AS now,
    SUM("Doanh thu đơn") FILTER (WHERE CAST("Ngày đặt" AS DATE) BETWEEN DATE '2026-02-01' AND DATE '2026-02-04') AS before
  FROM "don_tinh_doanh_thu"
)
```
