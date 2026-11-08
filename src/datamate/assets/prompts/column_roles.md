Bạn giúp chuẩn bị dữ liệu của một cửa hàng nhỏ ở Việt Nam. Dưới đây là các bảng và những CỘT mà hệ thống chưa biết vai trò (tên cột lạ, viết tắt, hoặc ghi chú). Với mỗi cột, hãy xác định nó có phải một trong các vai trò dưới đây không.

Các vai trò (mã: ý nghĩa):
{roles}

Quy tắc:
- CHỈ trả lời cho các cột được liệt kê dạng `- "tên cột"` trong phần các bảng. Không nhắc lại cột nào khác.
- Mỗi bảng đã nêu "Vai trò đã có trong bảng": đừng gán lại các vai trò đó cho cột khác.
- Chỉ gán vai trò khi CHẮC dựa trên tên cột và các giá trị mẫu. Không chắc thì bỏ qua cột đó (không viết dòng nào).
- Mỗi vai trò chỉ gán cho MỘT cột trong một bảng. Cột phụ (ghi chú tự do, điện thoại, địa chỉ...) bỏ qua.
- Cột `status` là trạng thái ĐƠN HÀNG (hoàn thành, huỷ, trả hàng, đang giao). Nếu cột chỉ ghi các trường hợp đặc biệt (vd. "huỷ", "đang giao") và ô trống nghĩa là đơn bình thường, đặt "blank_is": "hoan_thanh". "blank_is" nhận một trong: hoan_thanh, huy, tra_hang, dang_giao; chỉ dùng cho cột status.
- Ngày thu tiền / ngày thanh toán của một phiếu thu là `receipt_date`; số tiền của phiếu thu là `receipt_amount`; mã đơn trong bảng thu tiền là `order_id`.
- Tên bảng và tên cột phải giữ NGUYÊN VĂN như được liệt kê.

README của cửa hàng:
{readme}

Các bảng:
{tables}

Trả lời CHỈ bằng các dòng, mỗi dòng MỘT đối tượng JSON cho MỘT cột bạn gán được vai trò (bỏ qua mọi cột còn lại, không viết gì khác):
{"table": "<tên bảng>", "column": "<tên cột>", "role": "<mã vai trò>", "blank_is": null}
