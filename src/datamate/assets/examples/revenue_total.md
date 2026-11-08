mô tả: Tổng doanh thu một kỳ: cộng doanh thu đơn của các đơn có cờ tính doanh thu.

## pandas
```python
d = T["don_tinh_doanh_thu"]
d = d[P.day(2026, 3, 4).contains(d["Ngày đặt"])]
answer = {"type": "number", "answer": round_money(d["Doanh thu đơn"].sum())}
```

## sql
```sql
-- type: number
SELECT round_money(SUM("Doanh thu đơn")) FROM "don_tinh_doanh_thu"
WHERE CAST("Ngày đặt" AS DATE) = DATE '2026-03-04'
```
