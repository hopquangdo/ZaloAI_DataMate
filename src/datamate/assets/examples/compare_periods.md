mô tả: So sánh hai kỳ: tính cùng chỉ số cho từng kỳ rồi lấy phần trăm thay đổi (kỳ sau so với kỳ trước).

## pandas
```python
d = T["don_tinh_doanh_thu"]
now = d.loc[P.month(2026, 3).contains(d["Ngày đặt"]), "Doanh thu đơn"].sum()
before = d.loc[P.month(2026, 2).contains(d["Ngày đặt"]), "Doanh thu đơn"].sum()
answer = {"type": "percent", "answer": pct_change(now, before)}
```

## sql
```sql
-- type: percent
SELECT ROUND(100.0 * (now - before) / before, 2) FROM (
  SELECT
    SUM("Doanh thu đơn") FILTER (WHERE CAST("Ngày đặt" AS DATE) BETWEEN DATE '2026-03-01' AND DATE '2026-03-31') AS now,
    SUM("Doanh thu đơn") FILTER (WHERE CAST("Ngày đặt" AS DATE) BETWEEN DATE '2026-02-01' AND DATE '2026-02-28') AS before
  FROM "don_tinh_doanh_thu"
)
```
