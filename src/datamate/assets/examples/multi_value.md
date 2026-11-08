mô tả: Câu hỏi nhiều giá trị ('A và B lần lượt', 'theo thứ tự'): trả MỘT danh sách theo đúng thứ tự được hỏi, không trả bảng.

## pandas
```python
d = T["don_tinh_doanh_thu"]
d = d[P.month(2026, 3).contains(d["Ngày đặt"])]
by = d.groupby("Hình thức thanh toán")["Doanh thu đơn"].sum()
answer = {"type": "list", "answer": [round_money(by.get("Tiền mặt", 0)), round_money(by.get("Chuyển khoản", 0))]}
```

## sql
```sql
-- type: list  (nhiều giá trị: mỗi giá trị MỘT dòng, một cột, đúng thứ tự được hỏi)
SELECT v FROM (
  SELECT 1 AS o, round_money(COALESCE(SUM("Doanh thu đơn"), 0)) AS v FROM "don_tinh_doanh_thu"
  WHERE "Hình thức thanh toán" = 'Tiền mặt'
    AND CAST("Ngày đặt" AS DATE) BETWEEN DATE '2026-03-01' AND DATE '2026-03-31'
  UNION ALL
  SELECT 2, round_money(COALESCE(SUM("Doanh thu đơn"), 0)) FROM "don_tinh_doanh_thu"
  WHERE "Hình thức thanh toán" = 'Chuyển khoản'
    AND CAST("Ngày đặt" AS DATE) BETWEEN DATE '2026-03-01' AND DATE '2026-03-31'
) ORDER BY o
```
