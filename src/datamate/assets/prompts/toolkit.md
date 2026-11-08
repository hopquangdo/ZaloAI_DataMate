Tên có sẵn trong code (không import gì thêm):
- T: dict tên bảng → DataFrame (bản sao, sửa thoải mái). Cột ngày đã là datetime64, cột tiền/số đã là float.
- pd, np, math
- today: pd.Timestamp — "hôm nay" của câu hỏi (as_of_date); so sánh thẳng được với cột ngày (vd. `df["Ngày"] <= today`)
- P: các hàm kỳ thời gian (mọi Period đóng hai đầu, .start/.end là pd.Timestamp so sánh thẳng được với cột ngày, có .days, .contains(cột_datetime) → mask, .shift_back() → kỳ liền trước cùng số ngày):
    P.day(d) hoặc P.day(y, m, d), P.yesterday(today) hoặc P.previous_day(d) (= ngày liền trước), P.month(y, m), P.previous_month(y, m), P.same_month_last_year(y, m),
    P.year_of_month(m, today), P.this_month(today), P.last_month_same_days(today),
    P.this_week(today), P.last_week(today), P.last_n_days(today, n), P.quarter(y, q),
    P.year(y), P.year_to_date(today), P.until(d, data_start), P.Period(start, end)
- lunar: lịch âm; lunar.tet(Y) → Period dịp Tết năm Y, lunar.before_tet(Y), lunar.solar(năm_âm, tháng_âm, ngày_âm) → pd.Timestamp
- date, datetime, timedelta: như thư viện datetime (đã có sẵn, không cần import)
- norm(s): chuẩn hoá chuỗi như bộ chấm (chữ thường, bỏ dấu câu, GIỮ dấu tiếng Việt: norm("Đã hủy") == "đã hủy", KHÔNG so với "da huy")
- P.between(đầu, cuối): khoảng ngày BẤT KỲ (cả hai đầu tính), vd. P.between('2025-06-29', '2025-07-05').contains(cột_ngày). Nhiều ngày thì dùng P.between, KHÔNG dùng P.day.
- fold(s): chữ thường, bỏ dấu và bỏ dấu câu / ngoặc ("Cà phê (M)" ~ "ca phe m") — dùng để so khớp tên mặt hàng/khách/nhóm trong câu hỏi viết không dấu
- order_status(cột_trạng_thái) → Series nhãn chuẩn: 'hoan_thanh' | 'huy' | 'tra_hang' | 'dang_giao' | 'khac'. LUÔN dùng nó để lọc đơn; đơn tính doanh thu = nhãn thuộc ['hoan_thanh', 'dang_giao']. Kiểm tra không có nhãn 'khac' bất ngờ.
- round_money(x): làm tròn tiền về đồng, nửa lên
- pct(part, whole), pct_change(current, previous): phần trăm làm tròn 2 chữ số
- unanswerable(reason): gọi khi dữ liệu không có thông tin cần thiết (rulebook §7)
