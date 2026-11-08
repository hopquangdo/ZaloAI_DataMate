mô tả: Trung bình mỗi ngày thứ X của kỳ = tổng chia cho SỐ NGÀY thứ X trong kỳ, kể cả ngày không có đơn.

## pandas
```python
d = T["don_tinh_doanh_thu"]
period = P.month(2026, 3)
d = d[period.contains(d["Ngày đặt"]) & (d["Ngày đặt"].dt.dayofweek == 0)]
n_days = sum(1 for day in pd.date_range(period.start, period.end) if day.dayofweek == 0)
answer = {"type": "number", "answer": round_money(d["Doanh thu đơn"].sum() / n_days)}
```

## sql
```sql
-- type: number
SELECT round_money(
  (SELECT SUM("Doanh thu đơn") FROM "don_tinh_doanh_thu"
   WHERE CAST("Ngày đặt" AS DATE) BETWEEN DATE '2026-03-01' AND DATE '2026-03-31'
     AND dayofweek(CAST("Ngày đặt" AS DATE)) = 1)
  / (SELECT COUNT(*) FROM generate_series(DATE '2026-03-01', DATE '2026-03-31', INTERVAL 1 DAY) AS t(d)
     WHERE dayofweek(d) = 1))
```
