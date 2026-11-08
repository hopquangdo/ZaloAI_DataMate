mô tả: Khách trả nợ trong kỳ = tổng 'Số tiền thu' của các lần thu có 'Là trả nợ' = TRUE và ngày thu trong kỳ (kể cả đơn kỳ trước).

## pandas
```python
p = T["thanh_toan_chuan"]
p = p[p["Là trả nợ"] & P.month(2026, 3).contains(p["Ngày thu"])]
answer = {"type": "number", "answer": round_money(p["Số tiền thu"].sum())}
```

## sql
```sql
-- type: number
SELECT round_money(SUM("Số tiền thu")) FROM "thanh_toan_chuan"
WHERE "Là trả nợ" AND CAST("Ngày thu" AS DATE) BETWEEN DATE '2026-03-01' AND DATE '2026-03-31'
```
