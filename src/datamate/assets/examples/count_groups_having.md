mô tả: Đếm SỐ NHÓM thỏa điều kiện ('có mấy khách mua ít nhất N đơn', 'bao nhiêu mặt hàng có mặt trong ít nhất N đơn'): gom theo nhóm, lọc theo số đơn rồi ĐẾM các nhóm còn lại. Câu 'tỉ lệ khách mua từ N đơn' = số khách đó / tổng số khách có mua trong kỳ.

## pandas
```python
d = T["don_tinh_doanh_thu"]
d = d[P.month(2026, 3).contains(d["Ngày đặt"]) & d["Khách định danh"].notna()]
so_don = d.groupby("Khách định danh")["Mã đơn"].nunique()
answer = {"type": "number", "answer": int((so_don >= 4).sum())}
# mặt hàng trong ít nhất N đơn: dùng dong_hang_tinh_doanh_thu, groupby("Tên hàng")["Mã đơn"].nunique()
```

## sql
```sql
-- type: number
SELECT COUNT(*) FROM (
  SELECT "Khách định danh" FROM "don_tinh_doanh_thu"
  WHERE "Khách định danh" IS NOT NULL
    AND CAST("Ngày đặt" AS DATE) BETWEEN DATE '2026-03-01' AND DATE '2026-03-31'
  GROUP BY "Khách định danh" HAVING COUNT(DISTINCT "Mã đơn") >= 4
)
```
