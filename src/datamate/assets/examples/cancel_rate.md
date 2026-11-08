mô tả: Tỉ lệ đơn huỷ = số đơn huỷ / MỌI đơn đặt trong kỳ (mọi trạng thái), nhân 100, làm tròn 2 chữ số.

## pandas
```python
d = T["don_chuan"]
d = d[P.month(2026, 3).contains(d["Ngày đặt"])]
answer = {"type": "percent", "answer": pct((d["Trạng thái chuẩn"] == "huy").sum(), len(d))}
```

## sql
```sql
-- type: percent
SELECT ROUND(100.0 * COUNT(*) FILTER (WHERE "Trạng thái chuẩn" = 'huy') / COUNT(*), 2)
FROM "don_chuan"
WHERE CAST("Ngày đặt" AS DATE) BETWEEN DATE '2026-03-01' AND DATE '2026-03-31'
```
