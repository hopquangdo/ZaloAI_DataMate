mô tả: Doanh thu trung bình mỗi đơn = trung bình cột doanh thu đơn trên các đơn tính doanh thu của kỳ.

## pandas
```python
d = T["don_tinh_doanh_thu"]
d = d[P.month(2026, 3).contains(d["Ngày đặt"])]
answer = {"type": "number", "answer": round_money(d["Doanh thu đơn"].mean())}
```

## sql
```sql
-- type: number
SELECT round_money(AVG("Doanh thu đơn")) FROM "don_tinh_doanh_thu"
WHERE CAST("Ngày đặt" AS DATE) BETWEEN DATE '2026-03-01' AND DATE '2026-03-31'
```
