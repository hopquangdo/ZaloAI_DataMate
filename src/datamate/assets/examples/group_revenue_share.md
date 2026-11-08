mô tả: Doanh thu của một NHÓM hàng và tỉ trọng của nó: dùng bảng dòng hàng (nhóm hàng là cột của dòng hàng, tên cột xem mô tả bảng, vd. 'Nhóm hàng hóa'); tỉ trọng = tiền nhóm / tổng tiền mọi hàng cùng kỳ. KHÔNG dùng bảng đơn (không có cột nhóm hàng).

## pandas
```python
d = T["dong_hang_tinh_doanh_thu"]
d = d[P.month(2026, 3).contains(d["Ngày đặt"])]
nhom = d[d["Nhóm hàng hóa"].map(fold) == fold("thực phẩm")]
tien = nhom["Thành tiền dòng"].sum()
answer = {"type": "number", "answer": round_money(tien)}
# tỉ trọng: pct(tien, d["Thành tiền dòng"].sum())  -> type percent
```

## sql
```sql
-- type: number
SELECT round_money(SUM("Thành tiền dòng")) FROM "dong_hang_tinh_doanh_thu"
WHERE CAST("Ngày đặt" AS DATE) BETWEEN DATE '2026-03-01' AND DATE '2026-03-31'
  AND fold("Nhóm hàng hóa") = fold('thực phẩm')
-- tỉ trọng: chia cho SUM("Thành tiền dòng") của cùng kỳ (không lọc nhóm), nhân 100, type: percent
```
