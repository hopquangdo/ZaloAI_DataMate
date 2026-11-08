mô tả: 'Tháng nào / ngày nào cao nhất': kiểu date. Đáp án tháng ghi 'YYYY-MM', đáp án ngày ghi 'YYYY-MM-DD'; cộng doanh thu theo từng tháng (hoặc ngày) trong các kỳ được hỏi rồi lấy lớn nhất.

## pandas
```python
d = T["don_tinh_doanh_thu"]
d = d[P.between("2026-01-01", "2026-03-31").contains(d["Ngày đặt"])]
by_month = d.groupby(d["Ngày đặt"].dt.strftime("%Y-%m"))["Doanh thu đơn"].sum()
answer = {"type": "date", "answer": by_month.idxmax()}
# ngày cao nhất: groupby(d["Ngày đặt"].dt.strftime("%Y-%m-%d"))
```

## sql
```sql
-- type: date
SELECT strftime(CAST("Ngày đặt" AS DATE), '%Y-%m') AS thang FROM "don_tinh_doanh_thu"
WHERE CAST("Ngày đặt" AS DATE) BETWEEN DATE '2026-01-01' AND DATE '2026-03-31'
GROUP BY thang ORDER BY SUM("Doanh thu đơn") DESC LIMIT 1
```
