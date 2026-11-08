mô tả: Giá nhập bình quân của một mặt hàng trong tháng = tổng thành tiền nhập / tổng số lượng nhập (bình quân theo số lượng, không phải trung bình cộng giá), theo đơn vị nhập được hỏi, bỏ phiếu huỷ.

## pandas
```python
i = T["nhap_hang_chuan"]
i = i[(i["Trạng thái phiếu"] != "huy") & P.month(2026, 3).contains(i["Ngày nhập"])]
i = i[(i["Tên hàng"].map(fold) == fold("Mì Hảo Hảo tôm chua cay")) & (i["Đơn vị nhập"].map(fold) == fold("thùng"))]
answer = {"type": "number", "answer": round_money(i["Thành tiền nhập"].sum() / i["Số lượng nhập"].sum())}
```

## sql
```sql
-- type: number
SELECT round_money(SUM("Thành tiền nhập") / SUM("Số lượng nhập")) FROM "nhap_hang_chuan"
WHERE COALESCE("Trạng thái phiếu", '') <> 'huy'
  AND CAST("Ngày nhập" AS DATE) BETWEEN DATE '2026-03-01' AND DATE '2026-03-31'
  AND fold("Tên hàng") = fold('Mì Hảo Hảo tôm chua cay')
  AND fold("Đơn vị nhập") = fold('thùng')
```
