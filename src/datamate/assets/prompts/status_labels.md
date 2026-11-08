Bạn phân loại trạng thái đơn hàng của một cửa hàng nhỏ ở Việt Nam. Theo quy định, mỗi đơn có đúng MỘT trong bốn trạng thái:
- hoan_thanh: đơn đã bán xong (đã giao, đã nhận, thành công, khách đã lấy...)
- huy: đơn bị huỷ, không thành (khách huỷ, shop huỷ, giao không thành nên huỷ...)
- tra_hang: đơn có trả hàng / hoàn hàng (kể cả trả một phần)
- dang_giao: đơn đang trên đường giao hoặc đang chờ giao

Dưới đây là các cách ghi trạng thái lấy từ dữ liệu của cửa hàng. Xếp MỖI cách ghi vào đúng một nhãn.
Trả lời chỉ bằng một đối tượng JSON, khoá là cách ghi giữ NGUYÊN VĂN, giá trị là một trong: hoan_thanh, huy, tra_hang, dang_giao.

Các cách ghi:
{values}
