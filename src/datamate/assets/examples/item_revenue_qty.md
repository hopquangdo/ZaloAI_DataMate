mô tả: Doanh thu hoặc số lượng của MỘT mặt hàng: lọc bảng dòng hàng theo tên hàng (so khớp bằng fold ở cả hai vế).

## pandas
```python
d = T["dong_hang_tinh_doanh_thu"]
d = d[P.month(2026, 3).contains(d["Ngày đặt"])]
d = d[d["Tên hàng"].map(fold) == fold("Cà phê sữa")]
answer = {"type": "number", "answer": round_money(d["Thành tiền dòng"].sum())}
# số lượng: dùng d["Số lượng quy đổi"].sum() thay cho cột thành tiền
```

## sql
```sql
-- type: number
SELECT round_money(SUM("Thành tiền dòng")) FROM "dong_hang_tinh_doanh_thu"
WHERE CAST("Ngày đặt" AS DATE) BETWEEN DATE '2026-03-01' AND DATE '2026-03-31'
  AND fold("Tên hàng") = fold('Cà phê sữa')
-- số lượng: SUM("Số lượng quy đổi") thay cho cột thành tiền
```
