mô tả: Đổi giá từ ngày D: so số bán N ngày KỂ TỪ ngày D (gồm ngày D) với N ngày LIỀN TRƯỚC. Lấy hai khoảng ngày từ gợi ý thời gian; pandas dùng P.between(đầu, cuối) (KHÔNG dùng P.day cho nhiều ngày). % thay đổi = (sau − trước) / trước.

## pandas
```python
d = T["dong_hang_tinh_doanh_thu"]
d = d[d["Tên hàng"].map(fold) == fold("Phở Vifon bò")]
sau = d.loc[P.between("2025-06-29", "2025-07-05").contains(d["Ngày đặt"]), "Số lượng quy đổi"].sum()
truoc = d.loc[P.between("2025-06-22", "2025-06-28").contains(d["Ngày đặt"]), "Số lượng quy đổi"].sum()
answer = {"type": "percent", "answer": pct_change(sau, truoc)}
```

## sql
```sql
-- type: percent
SELECT ROUND(100.0 * (sau - truoc) / truoc, 2) FROM (
  SELECT
    SUM("Số lượng quy đổi") FILTER (WHERE CAST("Ngày đặt" AS DATE) BETWEEN DATE '2025-06-29' AND DATE '2025-07-05') AS sau,
    SUM("Số lượng quy đổi") FILTER (WHERE CAST("Ngày đặt" AS DATE) BETWEEN DATE '2025-06-22' AND DATE '2025-06-28') AS truoc
  FROM "dong_hang_tinh_doanh_thu" WHERE fold("Tên hàng") = fold('Phở Vifon bò')
)
```
