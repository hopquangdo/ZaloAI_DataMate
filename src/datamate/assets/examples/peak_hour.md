mô tả: Giờ cao điểm = khung MỘT GIỜ TRÒN theo 'Giờ đặt' có nhiều đơn nhất; đáp án là giờ bắt đầu khung (number).

## pandas
```python
d = T["don_tinh_doanh_thu"]
d = d[P.month(2026, 3).contains(d["Ngày đặt"])]
by_hour = d.groupby(d["Giờ đặt"].dt.hour)["Mã đơn"].count()
answer = {"type": "number", "answer": int(by_hour.sort_values(ascending=False).index[0])}
```

## sql
```sql
-- type: number
SELECT EXTRACT(hour FROM "Giờ đặt") AS gio FROM "don_tinh_doanh_thu"
WHERE CAST("Ngày đặt" AS DATE) BETWEEN DATE '2026-03-01' AND DATE '2026-03-31'
GROUP BY gio ORDER BY COUNT(*) DESC LIMIT 1
```
