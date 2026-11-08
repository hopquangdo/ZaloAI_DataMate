"""Ghi lại các file ví dụ mẫu (assets/examples) trên bảng chuẩn tắc. Chạy một lần khi đổi mẫu."""

from pathlib import Path

OUT = Path(__file__).resolve().parents[1] / "src" / "datamate" / "assets" / "examples"

EXAMPLES = {
    "count_orders": (
        r"bao nhieu don|\bso don|dem don|may don|may bill|bao nhieu bill",
        "Đếm số đơn bán được: đếm dòng của bảng đơn đã lọc (don_tinh_doanh_thu), không đếm dòng hàng.",
        '''d = T["don_tinh_doanh_thu"]
d = d[P.month(2026, 3).contains(d["Ngày đặt"])]
answer = {"type": "number", "answer": int(len(d))}''',
        '''-- type: number
SELECT COUNT(*) FROM "don_tinh_doanh_thu"
WHERE CAST("Ngày đặt" AS DATE) BETWEEN DATE '2026-03-01' AND DATE '2026-03-31\'''',
    ),
    "cancel_count": (
        r"(don|bill|hoa don).*huy|huy.*(don|bill)",
        "Đếm đơn bị huỷ: đếm theo trạng thái chuẩn 'huy' trên bảng đơn, không lọc cờ tính doanh thu.",
        '''d = T["don_chuan"]
d = d[(d["Trạng thái chuẩn"] == "huy") & P.month(2026, 3).contains(d["Ngày đặt"])]
answer = {"type": "number", "answer": int(len(d))}''',
        '''-- type: number
SELECT COUNT(*) FROM "don_chuan"
WHERE "Trạng thái chuẩn" = 'huy'
  AND CAST("Ngày đặt" AS DATE) BETWEEN DATE '2026-03-01' AND DATE '2026-03-31\'''',
    ),
    "avg_per_order": (
        r"trung binh (moi |mot |tren mot )?(don|bill)|binh quan (moi )?(don|bill)|gia tri (trung binh )?(mot )?don",
        "Doanh thu trung bình mỗi đơn = trung bình cột doanh thu đơn trên các đơn tính doanh thu của kỳ.",
        '''d = T["don_tinh_doanh_thu"]
d = d[P.month(2026, 3).contains(d["Ngày đặt"])]
answer = {"type": "number", "answer": round_money(d["Doanh thu đơn"].mean())}''',
        '''-- type: number
SELECT round_money(AVG("Doanh thu đơn")) FROM "don_tinh_doanh_thu"
WHERE CAST("Ngày đặt" AS DATE) BETWEEN DATE '2026-03-01' AND DATE '2026-03-31\'''',
    ),
    "cancel_rate": (
        r"t[yi] le.*(huy|tra)|(huy|tra).*(%|phan tram|t[yi] le)|phan tram don",
        "Tỉ lệ đơn huỷ = số đơn huỷ / MỌI đơn đặt trong kỳ (mọi trạng thái), nhân 100, làm tròn 2 chữ số.",
        '''d = T["don_chuan"]
d = d[P.month(2026, 3).contains(d["Ngày đặt"])]
answer = {"type": "percent", "answer": pct((d["Trạng thái chuẩn"] == "huy").sum(), len(d))}''',
        '''-- type: percent
SELECT ROUND(100.0 * COUNT(*) FILTER (WHERE "Trạng thái chuẩn" = 'huy') / COUNT(*), 2)
FROM "don_chuan"
WHERE CAST("Ngày đặt" AS DATE) BETWEEN DATE '2026-03-01' AND DATE '2026-03-31\'''',
    ),
    "revenue_total": (
        r"doanh thu|dthu|tong tien|ban duoc bao nhieu|thu duoc|tien ban|thu ve",
        "Tổng doanh thu một kỳ: cộng doanh thu đơn của các đơn có cờ tính doanh thu.",
        '''d = T["don_tinh_doanh_thu"]
d = d[P.day(2026, 3, 4).contains(d["Ngày đặt"])]
answer = {"type": "number", "answer": round_money(d["Doanh thu đơn"].sum())}''',
        '''-- type: number
SELECT round_money(SUM("Doanh thu đơn")) FROM "don_tinh_doanh_thu"
WHERE CAST("Ngày đặt" AS DATE) = DATE '2026-03-04\'''',
    ),
    "item_revenue_qty": (
        r"(ban|thu).*(tien|duoc).*(ly|chai|hop|goi|cai|kg|phan|cuon|thung)|(so|tong).*(luong|ly|chai|hop|goi|kg)|tien ban .*(cua|hang|mon)",
        "Doanh thu hoặc số lượng của MỘT mặt hàng: lọc bảng dòng hàng theo tên hàng (so khớp bằng fold ở cả hai vế).",
        '''d = T["dong_hang_tinh_doanh_thu"]
d = d[P.month(2026, 3).contains(d["Ngày đặt"])]
d = d[d["Tên hàng"].map(fold) == fold("Cà phê sữa")]
answer = {"type": "number", "answer": round_money(d["Thành tiền dòng"].sum())}
# số lượng: dùng d["Số lượng quy đổi"].sum() thay cho cột thành tiền''',
        '''-- type: number
SELECT round_money(SUM("Thành tiền dòng")) FROM "dong_hang_tinh_doanh_thu"
WHERE CAST("Ngày đặt" AS DATE) BETWEEN DATE '2026-03-01' AND DATE '2026-03-31'
  AND fold("Tên hàng") = fold('Cà phê sữa')
-- số lượng: SUM("Số lượng quy đổi") thay cho cột thành tiền''',
    ),
    "top_n": (
        r"nhieu nhat|cao nhat|\btop\b|xep hang|ban chay|thap nhat|it nhat|dung dau|\bhot\b",
        "Xếp hạng hàng bán chạy theo SỐ LƯỢNG QUY ĐỔI (không theo số dòng hay số tiền), bỏ đơn huỷ/trả.",
        '''d = T["dong_hang_tinh_doanh_thu"]
d = d[P.month(2026, 3).contains(d["Ngày đặt"])]
top = d.groupby("Tên hàng")["Số lượng quy đổi"].sum().sort_values(ascending=False).head(3)
answer = {"type": "list", "answer": list(top.index)}''',
        '''-- type: list
SELECT "Tên hàng" FROM "dong_hang_tinh_doanh_thu"
WHERE CAST("Ngày đặt" AS DATE) BETWEEN DATE '2026-03-01' AND DATE '2026-03-31'
GROUP BY "Tên hàng"
ORDER BY SUM("Số lượng quy đổi") DESC
LIMIT 3''',
    ),
    "compare_periods": (
        r"so voi|\btang\b|\bgiam\b|tang truong|chenh lech|cung ky|hon hay kem",
        "So sánh hai kỳ: tính cùng chỉ số cho từng kỳ rồi lấy phần trăm thay đổi (kỳ sau so với kỳ trước).",
        '''d = T["don_tinh_doanh_thu"]
now = d.loc[P.month(2026, 3).contains(d["Ngày đặt"]), "Doanh thu đơn"].sum()
before = d.loc[P.month(2026, 2).contains(d["Ngày đặt"]), "Doanh thu đơn"].sum()
answer = {"type": "percent", "answer": pct_change(now, before)}''',
        '''-- type: percent
SELECT ROUND(100.0 * (now - before) / before, 2) FROM (
  SELECT
    SUM("Doanh thu đơn") FILTER (WHERE CAST("Ngày đặt" AS DATE) BETWEEN DATE '2026-03-01' AND DATE '2026-03-31') AS now,
    SUM("Doanh thu đơn") FILTER (WHERE CAST("Ngày đặt" AS DATE) BETWEEN DATE '2026-02-01' AND DATE '2026-02-28') AS before
  FROM "don_tinh_doanh_thu"
)''',
    ),
    "gross_profit": (
        "",
        "Lãi gộp = tổng cột 'Lãi gộp dòng' (thành tiền − số lượng × giá vốn ghi trên dòng) của bảng dòng hàng đã lọc; không tính lại giá vốn từ phiếu nhập.",
        '''d = T["dong_hang_tinh_doanh_thu"]
d = d[P.month(2026, 3).contains(d["Ngày đặt"])]
answer = {"type": "number", "answer": round_money(d["Lãi gộp dòng"].sum())}''',
        '''-- type: number
SELECT round_money(SUM("Lãi gộp dòng")) FROM "dong_hang_tinh_doanh_thu"
WHERE CAST("Ngày đặt" AS DATE) BETWEEN DATE '2026-03-01' AND DATE '2026-03-31\'''',
    ),
    "debt_repayment": (
        "",
        "Khách trả nợ trong kỳ = tổng 'Số tiền thu' của các lần thu có 'Là trả nợ' = TRUE và ngày thu trong kỳ (kể cả đơn kỳ trước).",
        '''p = T["thanh_toan_chuan"]
p = p[p["Là trả nợ"] & P.month(2026, 3).contains(p["Ngày thu"])]
answer = {"type": "number", "answer": round_money(p["Số tiền thu"].sum())}''',
        '''-- type: number
SELECT round_money(SUM("Số tiền thu")) FROM "thanh_toan_chuan"
WHERE "Là trả nợ" AND CAST("Ngày thu" AS DATE) BETWEEN DATE '2026-03-01' AND DATE '2026-03-31\'''',
    ),
    "days_over_threshold": (
        "",
        "Đếm số NGÀY đạt ngưỡng doanh thu: cộng doanh thu theo từng ngày trước, rồi mới so với ngưỡng (không so từng đơn).",
        '''d = T["don_tinh_doanh_thu"]
d = d[P.month(2026, 3).contains(d["Ngày đặt"])]
by_day = d.groupby(d["Ngày đặt"].dt.date)["Doanh thu đơn"].sum()
answer = {"type": "number", "answer": int((by_day >= 10_000_000).sum())}''',
        '''-- type: number
SELECT COUNT(*) FROM (
  SELECT CAST("Ngày đặt" AS DATE) AS ngay FROM "don_tinh_doanh_thu"
  WHERE CAST("Ngày đặt" AS DATE) BETWEEN DATE '2026-03-01' AND DATE '2026-03-31'
  GROUP BY ngay HAVING SUM("Doanh thu đơn") >= 10000000
)''',
    ),
    "by_shift": (
        "",
        "Theo ca: lọc cột 'Ca' (sáng / chiều) có sẵn, không tự đoán giờ. Đếm đơn hay doanh thu thì dùng bảng đơn đã lọc.",
        '''d = T["don_tinh_doanh_thu"]
d = d[(d["Ca"] == "chiều") & P.month(2026, 3).contains(d["Ngày đặt"])]
answer = {"type": "number", "answer": int(len(d))}''',
        '''-- type: number
SELECT COUNT(*) FROM "don_tinh_doanh_thu"
WHERE "Ca" = 'chiều'
  AND CAST("Ngày đặt" AS DATE) BETWEEN DATE '2026-03-01' AND DATE '2026-03-31\'''',
    ),
    "multi_value": (
        "",
        "Câu hỏi nhiều giá trị ('A và B lần lượt', 'theo thứ tự'): trả MỘT danh sách theo đúng thứ tự được hỏi, không trả bảng.",
        '''d = T["don_tinh_doanh_thu"]
d = d[P.month(2026, 3).contains(d["Ngày đặt"])]
by = d.groupby("Hình thức thanh toán")["Doanh thu đơn"].sum()
answer = {"type": "list", "answer": [round_money(by.get("Tiền mặt", 0)), round_money(by.get("Chuyển khoản", 0))]}''',
        '''-- type: list  (nhiều giá trị: mỗi giá trị MỘT dòng, một cột, đúng thứ tự được hỏi)
SELECT v FROM (
  SELECT 1 AS o, round_money(COALESCE(SUM("Doanh thu đơn"), 0)) AS v FROM "don_tinh_doanh_thu"
  WHERE "Hình thức thanh toán" = 'Tiền mặt'
    AND CAST("Ngày đặt" AS DATE) BETWEEN DATE '2026-03-01' AND DATE '2026-03-31'
  UNION ALL
  SELECT 2, round_money(COALESCE(SUM("Doanh thu đơn"), 0)) FROM "don_tinh_doanh_thu"
  WHERE "Hình thức thanh toán" = 'Chuyển khoản'
    AND CAST("Ngày đặt" AS DATE) BETWEEN DATE '2026-03-01' AND DATE '2026-03-31'
) ORDER BY o''',
    ),
    "top_customers": (
        "",
        "Xếp hạng khách: nhóm theo 'Khách định danh' (đã loại khách lẻ), trả 'Tên khách'. Khách mua nhiều tiền nhất xếp theo doanh thu.",
        """d = T["don_tinh_doanh_thu"]
d = d[P.month(2026, 3).contains(d["Ngày đặt"]) & d["Khách định danh"].notna()]
rank = d.groupby("Khách định danh").agg(ten=("Tên khách", "first"), tien=("Doanh thu đơn", "sum"))
top = rank.sort_values("tien", ascending=False).head(3)
answer = {"type": "list", "answer": list(top["ten"])}""",
        """-- type: list
SELECT any_value("Tên khách") FROM "don_tinh_doanh_thu"
WHERE "Khách định danh" IS NOT NULL
  AND CAST("Ngày đặt" AS DATE) BETWEEN DATE '2026-03-01' AND DATE '2026-03-31'
GROUP BY "Khách định danh"
ORDER BY SUM("Doanh thu đơn") DESC
LIMIT 3""",
    ),
    "loyal_customer": (
        "",
        "Khách trung thành nhất = khách có NHIỀU NGÀY CÓ MUA nhất trong kỳ (đếm ngày khác nhau, không đếm đơn).",
        """d = T["don_tinh_doanh_thu"]
d = d[P.month(2026, 3).contains(d["Ngày đặt"]) & d["Khách định danh"].notna()]
days = d.groupby("Khách định danh")["Ngày đặt"].apply(lambda s: s.dt.date.nunique())
best = days.sort_values(ascending=False).index[0]
answer = {"type": "string", "answer": d.loc[d["Khách định danh"] == best, "Tên khách"].iloc[0]}""",
        """-- type: string
SELECT any_value("Tên khách") FROM "don_tinh_doanh_thu"
WHERE "Khách định danh" IS NOT NULL
  AND CAST("Ngày đặt" AS DATE) BETWEEN DATE '2026-03-01' AND DATE '2026-03-31'
GROUP BY "Khách định danh"
ORDER BY COUNT(DISTINCT CAST("Ngày đặt" AS DATE)) DESC
LIMIT 1""",
    ),
    "big_spender": (
        "",
        "Khách sộp nhất = giá trị TRUNG BÌNH một đơn cao nhất, chỉ xét khách có từ 3 đơn trở lên trong kỳ. Khách hay đổi ý = nhiều đơn huỷ nhất (dùng bảng đầy đủ don_chuan).",
        """d = T["don_tinh_doanh_thu"]
d = d[P.month(2026, 3).contains(d["Ngày đặt"]) & d["Khách định danh"].notna()]
g = d.groupby("Khách định danh").agg(ten=("Tên khách", "first"), so_don=("Mã đơn", "count"), tb=("Doanh thu đơn", "mean"))
g = g[g["so_don"] >= 3].sort_values("tb", ascending=False)
answer = {"type": "string", "answer": g["ten"].iloc[0]}""",
        """-- type: string
SELECT any_value("Tên khách") FROM "don_tinh_doanh_thu"
WHERE "Khách định danh" IS NOT NULL
  AND CAST("Ngày đặt" AS DATE) BETWEEN DATE '2026-03-01' AND DATE '2026-03-31'
GROUP BY "Khách định danh"
HAVING COUNT(*) >= 3
ORDER BY AVG("Doanh thu đơn") DESC
LIMIT 1""",
    ),
    "peak_hour": (
        "",
        "Giờ cao điểm = khung MỘT GIỜ TRÒN theo 'Giờ đặt' có nhiều đơn nhất; đáp án là giờ bắt đầu khung (number).",
        """d = T["don_tinh_doanh_thu"]
d = d[P.month(2026, 3).contains(d["Ngày đặt"])]
by_hour = d.groupby(d["Giờ đặt"].dt.hour)["Mã đơn"].count()
answer = {"type": "number", "answer": int(by_hour.sort_values(ascending=False).index[0])}""",
        """-- type: number
SELECT EXTRACT(hour FROM "Giờ đặt") AS gio FROM "don_tinh_doanh_thu"
WHERE CAST("Ngày đặt" AS DATE) BETWEEN DATE '2026-03-01' AND DATE '2026-03-31'
GROUP BY gio ORDER BY COUNT(*) DESC LIMIT 1""",
    ),
    "weekday_average": (
        "",
        "Trung bình mỗi ngày thứ X của kỳ = tổng chia cho SỐ NGÀY thứ X trong kỳ, kể cả ngày không có đơn.",
        """d = T["don_tinh_doanh_thu"]
period = P.month(2026, 3)
d = d[period.contains(d["Ngày đặt"]) & (d["Ngày đặt"].dt.dayofweek == 0)]
n_days = sum(1 for day in pd.date_range(period.start, period.end) if day.dayofweek == 0)
answer = {"type": "number", "answer": round_money(d["Doanh thu đơn"].sum() / n_days)}""",
        """-- type: number
SELECT round_money(
  (SELECT SUM("Doanh thu đơn") FROM "don_tinh_doanh_thu"
   WHERE CAST("Ngày đặt" AS DATE) BETWEEN DATE '2026-03-01' AND DATE '2026-03-31'
     AND dayofweek(CAST("Ngày đặt" AS DATE)) = 1)
  / (SELECT COUNT(*) FROM generate_series(DATE '2026-03-01', DATE '2026-03-31', INTERVAL 1 DAY) AS t(d)
     WHERE dayofweek(d) = 1))""",
    ),
    "same_period_compare": (
        "",
        "So với CÙNG KỲ tháng trước: kỳ này là từ đầu tháng đến hết hôm nay; kỳ trước là tháng trước có cùng số ngày (dùng khoảng ngày đã cho trong gợi ý thời gian). Phần trăm thay đổi = (kỳ này − kỳ trước) / kỳ trước.",
        """d = T["don_tinh_doanh_thu"]
now = d.loc[P.this_month(today).contains(d["Ngày đặt"]), "Doanh thu đơn"].sum()
before = d.loc[P.last_month_same_days(today).contains(d["Ngày đặt"]), "Doanh thu đơn"].sum()
answer = {"type": "percent", "answer": pct_change(now, before)}""",
        """-- type: percent
-- (thay hai khoảng ngày bằng khoảng ngày trong gợi ý: tháng này đến hết hôm nay; tháng trước cùng số ngày)
SELECT ROUND(100.0 * (now - before) / before, 2) FROM (
  SELECT
    SUM("Doanh thu đơn") FILTER (WHERE CAST("Ngày đặt" AS DATE) BETWEEN DATE '2026-03-01' AND DATE '2026-03-04') AS now,
    SUM("Doanh thu đơn") FILTER (WHERE CAST("Ngày đặt" AS DATE) BETWEEN DATE '2026-02-01' AND DATE '2026-02-04') AS before
  FROM "don_tinh_doanh_thu"
)""",
    ),
    "customer_balance": (
        "",
        "Dư nợ của khách đến hết ngày D = tổng 'Nợ thêm' của đơn đặt đến D trừ tổng tiền trả nợ ('Là trả nợ') thu đến D, theo 'Khách định danh'. Đếm khách còn nợ / xếp hạng khách nợ nhiều nhất: dùng dư nợ > 0. Dùng bảng đầy đủ don_chuan và thanh_toan_chuan.",
        """o = T["don_chuan"]
o = o[o["Khách định danh"].notna() & (o["Ngày đặt"] <= pd.Timestamp("2026-03-04"))]
p = T["thanh_toan_chuan"]
p = p[p["Là trả nợ"] & p["Khách định danh"].notna() & (p["Ngày thu"] < pd.Timestamp("2026-03-05"))]
owed = o.groupby("Khách định danh")["Nợ thêm"].sum().sub(p.groupby("Khách định danh")["Số tiền thu"].sum(), fill_value=0)
owed = owed[owed > 0]
answer = {"type": "number", "answer": int(len(owed))}
# top 3 khách nợ nhiều nhất: owed.sort_values(ascending=False).head(3); tên khách lấy từ cột 'Tên khách'""",
        """-- type: number
WITH no_them AS (
  SELECT "Khách định danh" AS k, SUM("Nợ thêm") AS v FROM "don_chuan"
  WHERE "Khách định danh" IS NOT NULL AND CAST("Ngày đặt" AS DATE) <= DATE '2026-03-04' GROUP BY k
), tra_no AS (
  SELECT "Khách định danh" AS k, SUM("Số tiền thu") AS v FROM "thanh_toan_chuan"
  WHERE "Là trả nợ" AND "Khách định danh" IS NOT NULL AND CAST("Ngày thu" AS DATE) <= DATE '2026-03-04' GROUP BY k
)
SELECT COUNT(*) FROM no_them LEFT JOIN tra_no USING (k)
WHERE no_them.v - COALESCE(tra_no.v, 0) > 0""",
    ),
    "avg_import_price": (
        "",
        "Giá nhập bình quân của một mặt hàng trong tháng = tổng thành tiền nhập / tổng số lượng nhập (bình quân theo số lượng, không phải trung bình cộng giá), theo đơn vị nhập được hỏi, bỏ phiếu huỷ.",
        """i = T["nhap_hang_chuan"]
i = i[(i["Trạng thái phiếu"] != "huy") & P.month(2026, 3).contains(i["Ngày nhập"])]
i = i[(i["Tên hàng"].map(fold) == fold("Mì Hảo Hảo tôm chua cay")) & (i["Đơn vị nhập"].map(fold) == fold("thùng"))]
answer = {"type": "number", "answer": round_money(i["Thành tiền nhập"].sum() / i["Số lượng nhập"].sum())}""",
        """-- type: number
SELECT round_money(SUM("Thành tiền nhập") / SUM("Số lượng nhập")) FROM "nhap_hang_chuan"
WHERE COALESCE("Trạng thái phiếu", '') <> 'huy'
  AND CAST("Ngày nhập" AS DATE) BETWEEN DATE '2026-03-01' AND DATE '2026-03-31'
  AND fold("Tên hàng") = fold('Mì Hảo Hảo tôm chua cay')
  AND fold("Đơn vị nhập") = fold('thùng')""",
    ),
    "debt_table": (
        "",
        "Bảng khách nợ nhiều nhất đến hết ngày D: cột đặt tên không dấu dạng snake_case (khach_hang, so_tien_no); ô số là number. Dư nợ = nợ thêm − trả nợ theo 'Khách định danh'.",
        """o = T["don_chuan"]
o = o[o["Khách định danh"].notna() & (o["Ngày đặt"] <= pd.Timestamp("2026-03-04"))]
p = T["thanh_toan_chuan"]
p = p[p["Là trả nợ"] & p["Khách định danh"].notna() & (p["Ngày thu"] < pd.Timestamp("2026-03-05"))]
owed = o.groupby("Khách định danh")["Nợ thêm"].sum().sub(p.groupby("Khách định danh")["Số tiền thu"].sum(), fill_value=0)
names = o.drop_duplicates("Khách định danh").set_index("Khách định danh")["Tên khách"]
top = owed.sort_values(ascending=False).head(3)
rows = [[names[k], round_money(v)] for k, v in top.items()]
answer = {"type": "table", "answer": {"columns": ["khach_hang", "so_tien_no"], "rows": rows}}""",
        """-- type: table
WITH no_them AS (
  SELECT "Khách định danh" AS k, any_value("Tên khách") AS ten, SUM("Nợ thêm") AS v FROM "don_chuan"
  WHERE "Khách định danh" IS NOT NULL AND CAST("Ngày đặt" AS DATE) <= DATE '2026-03-04' GROUP BY k
), tra_no AS (
  SELECT "Khách định danh" AS k, SUM("Số tiền thu") AS v FROM "thanh_toan_chuan"
  WHERE "Là trả nợ" AND "Khách định danh" IS NOT NULL AND CAST("Ngày thu" AS DATE) <= DATE '2026-03-04' GROUP BY k
)
SELECT ten AS khach_hang, round_money(no_them.v - COALESCE(tra_no.v, 0)) AS so_tien_no
FROM no_them LEFT JOIN tra_no USING (k)
ORDER BY so_tien_no DESC LIMIT 3""",
    ),
    "count_groups_having": (
        "",
        "Đếm SỐ NHÓM thỏa điều kiện ('có mấy khách mua ít nhất N đơn', 'bao nhiêu mặt hàng có mặt trong ít nhất N đơn'): gom theo nhóm, lọc theo số đơn rồi ĐẾM các nhóm còn lại. Câu 'tỉ lệ khách mua từ N đơn' = số khách đó / tổng số khách có mua trong kỳ.",
        """d = T["don_tinh_doanh_thu"]
d = d[P.month(2026, 3).contains(d["Ngày đặt"]) & d["Khách định danh"].notna()]
so_don = d.groupby("Khách định danh")["Mã đơn"].nunique()
answer = {"type": "number", "answer": int((so_don >= 4).sum())}
# mặt hàng trong ít nhất N đơn: dùng dong_hang_tinh_doanh_thu, groupby("Tên hàng")["Mã đơn"].nunique()""",
        """-- type: number
SELECT COUNT(*) FROM (
  SELECT "Khách định danh" FROM "don_tinh_doanh_thu"
  WHERE "Khách định danh" IS NOT NULL
    AND CAST("Ngày đặt" AS DATE) BETWEEN DATE '2026-03-01' AND DATE '2026-03-31'
  GROUP BY "Khách định danh" HAVING COUNT(DISTINCT "Mã đơn") >= 4
)""",
    ),
    "best_period": (
        "",
        "'Tháng nào / ngày nào cao nhất': kiểu date. Đáp án tháng ghi 'YYYY-MM', đáp án ngày ghi 'YYYY-MM-DD'; cộng doanh thu theo từng tháng (hoặc ngày) trong các kỳ được hỏi rồi lấy lớn nhất.",
        """d = T["don_tinh_doanh_thu"]
d = d[P.between("2026-01-01", "2026-03-31").contains(d["Ngày đặt"])]
by_month = d.groupby(d["Ngày đặt"].dt.strftime("%Y-%m"))["Doanh thu đơn"].sum()
answer = {"type": "date", "answer": by_month.idxmax()}
# ngày cao nhất: groupby(d["Ngày đặt"].dt.strftime("%Y-%m-%d"))""",
        """-- type: date
SELECT strftime(CAST("Ngày đặt" AS DATE), '%Y-%m') AS thang FROM "don_tinh_doanh_thu"
WHERE CAST("Ngày đặt" AS DATE) BETWEEN DATE '2026-01-01' AND DATE '2026-03-31'
GROUP BY thang ORDER BY SUM("Doanh thu đơn") DESC LIMIT 1""",
    ),
    "item_variant": (
        "",
        "Biến thể ghi trong tên hàng ('ly size L', 'loại M', vị...): gom MỌI mặt hàng có hậu tố đó, cộng số lượng. Tên thường kết thúc bằng '(L)' nên lọc theo hậu tố, không tìm 'size L'.",
        """d = T["dong_hang_tinh_doanh_thu"]
d = d[P.month(2026, 3).contains(d["Ngày đặt"])]
d = d[d["Tên hàng"].astype(str).str.strip().str.endswith("(L)")]
answer = {"type": "number", "answer": int(d["Số lượng quy đổi"].sum())}""",
        """-- type: number
SELECT COALESCE(SUM("Số lượng quy đổi"), 0) FROM "dong_hang_tinh_doanh_thu"
WHERE CAST("Ngày đặt" AS DATE) BETWEEN DATE '2026-03-01' AND DATE '2026-03-31'
  AND trim("Tên hàng") LIKE '%(L)'""",
    ),
    "price_change_window": (
        "",
        "Đổi giá từ ngày D: so số bán N ngày KỂ TỪ ngày D (gồm ngày D) với N ngày LIỀN TRƯỚC. Lấy hai khoảng ngày từ gợi ý thời gian; pandas dùng P.between(đầu, cuối) (KHÔNG dùng P.day cho nhiều ngày). % thay đổi = (sau − trước) / trước.",
        """d = T["dong_hang_tinh_doanh_thu"]
d = d[d["Tên hàng"].map(fold) == fold("Phở Vifon bò")]
sau = d.loc[P.between("2025-06-29", "2025-07-05").contains(d["Ngày đặt"]), "Số lượng quy đổi"].sum()
truoc = d.loc[P.between("2025-06-22", "2025-06-28").contains(d["Ngày đặt"]), "Số lượng quy đổi"].sum()
answer = {"type": "percent", "answer": pct_change(sau, truoc)}""",
        """-- type: percent
SELECT ROUND(100.0 * (sau - truoc) / truoc, 2) FROM (
  SELECT
    SUM("Số lượng quy đổi") FILTER (WHERE CAST("Ngày đặt" AS DATE) BETWEEN DATE '2025-06-29' AND DATE '2025-07-05') AS sau,
    SUM("Số lượng quy đổi") FILTER (WHERE CAST("Ngày đặt" AS DATE) BETWEEN DATE '2025-06-22' AND DATE '2025-06-28') AS truoc
  FROM "dong_hang_tinh_doanh_thu" WHERE fold("Tên hàng") = fold('Phở Vifon bò')
)""",
    ),
    "group_revenue_share": (
        "",
        "Doanh thu của một NHÓM hàng và tỉ trọng của nó: dùng bảng dòng hàng (nhóm hàng là cột của dòng hàng, tên cột xem mô tả bảng, vd. 'Nhóm hàng hóa'); tỉ trọng = tiền nhóm / tổng tiền mọi hàng cùng kỳ. KHÔNG dùng bảng đơn (không có cột nhóm hàng).",
        """d = T["dong_hang_tinh_doanh_thu"]
d = d[P.month(2026, 3).contains(d["Ngày đặt"])]
nhom = d[d["Nhóm hàng hóa"].map(fold) == fold("thực phẩm")]
tien = nhom["Thành tiền dòng"].sum()
answer = {"type": "number", "answer": round_money(tien)}
# tỉ trọng: pct(tien, d["Thành tiền dòng"].sum())  -> type percent""",
        """-- type: number
SELECT round_money(SUM("Thành tiền dòng")) FROM "dong_hang_tinh_doanh_thu"
WHERE CAST("Ngày đặt" AS DATE) BETWEEN DATE '2026-03-01' AND DATE '2026-03-31'
  AND fold("Nhóm hàng hóa") = fold('thực phẩm')
-- tỉ trọng: chia cho SUM("Thành tiền dòng") của cùng kỳ (không lọc nhóm), nhân 100, type: percent""",
    ),
    "unanswerable": (
        r"ton kho|gioi tinh|nhap hang|loi nhuan rong|dia chi|danh gia|hai long",
        "Khi dữ liệu không có thông tin cần thiết (không có cột liên quan) thì nói rõ là không trả lời được.",
        '''unanswerable("Dữ liệu không ghi tồn kho")''',
        '''-- unanswerable: dữ liệu không ghi tồn kho''',
    ),
}


def main() -> None:
    for name, (_triggers, description, pandas_code, sql_code) in EXAMPLES.items():
        text = (
            f"mô tả: {description}\n\n"
            f"## pandas\n```python\n{pandas_code}\n```\n\n"
            f"## sql\n```sql\n{sql_code}\n```\n"
        )
        (OUT / f"{name}.md").write_text(text, encoding="utf-8")
    print(f"đã ghi {len(EXAMPLES)} ví dụ vào {OUT}")


if __name__ == "__main__":
    main()
