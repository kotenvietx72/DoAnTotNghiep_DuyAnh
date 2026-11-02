# EPU Energy — Giám sát dòng điện và điện áp

Web Flask + Socket.IO quản lý **Phòng học**, **Kí túc xá**, **Phòng bảo vệ**. Giao diện rút gọn, sơ đồ SVG 2D tự vẽ, chỉ hiển thị dòng điện (A) và điện áp (V).

## Chạy trên Windows

Nhấp đúp `start.bat`, hoặc chạy trong thư mục dự án:

```powershell
.\run.ps1
```

Mở **http://127.0.0.1:5000**. Dừng bằng Ctrl+C. Trên máy khác, tạo lại môi trường Python 3.12 trở lên:

```powershell
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
.\.venv\Scripts\python.exe app.py
```

## Sử dụng

1. Mở chi tiết phòng từ thanh điều hướng hoặc thẻ phòng.
2. Nhấn thiết bị trên sơ đồ hoặc công tắc. Nút **Bật tất cả** ở từng phòng bật toàn bộ thiết bị của riêng phòng đó bằng một lệnh; nút bị khóa khi đang gửi lệnh, mất kết nối hoặc ở kịch bản tự động. Mỗi thiết bị có dòng điện tham chiếu riêng, xem [bảng model và nguồn](DEVICE_REFERENCES.md).
3. Dòng điện phòng bằng tổng A của thiết bị đang bật. Tắt hết: **0 A**; điện áp nguồn vẫn là **220 V**.
4. Ô **Tổng dòng điện** cộng dòng của ba nhánh phòng trong mô hình một pha dùng chung nguồn. Điện áp các nhánh không cộng với nhau.
5. **Cài đặt** cho phép chỉnh dòng thiết bị và hai ngưỡng cảnh báo/nguy hiểm, đều bằng A. Lưu để áp dụng ngay. **Khôi phục mặc định** yêu cầu xác nhận rồi đưa các thông số này của cả ba phòng về mặc định trong code; thay bản nháp chưa lưu, giữ công tắc thủ công và lịch sử phiên. Ở chế độ tự động, tổ hợp thiết bị được tính lại ngay theo thông số mới.
6. **Khởi động lấy mẫu** để ghi biểu đồ và thời lượng. **Dừng** ngừng ghi lịch sử; công tắc vẫn hoạt động.
7. **Kịch bản tự động** tự chọn tổ hợp thiết bị gần mức tải ngẫu nhiên mục tiêu nhất; số đo hiển thị bằng tổng dòng của đúng các thiết bị được bật trên sơ đồ. Kịch bản ưu tiên ba mức An toàn/Cảnh báo/Nguy hiểm nếu cấu hình hiện hành có tổ hợp đạt được; không tạo tải vượt khả năng thiết bị để ép trạng thái. Dừng lấy mẫu giữ mẫu cuối; dừng và chuyển về **Theo thiết bị** để khôi phục các công tắc thủ công đã lưu.
8. **Phân tích nội bộ** đọc Excel/CSV ba cột: thời gian, điện áp, dòng điện. Chọn phòng hoặc cấu hình một pha gốc 25/40 A, xem biểu đồ và xuất PDF.

Mô hình ba phòng dùng bố cục đã duyệt: bàn giáo viên gần bảng, Đ3/Đ6 lệch phải khỏi bàn sinh viên; kí túc xá có cửa và lối đi giữa, đèn theo tâm hai giường; phòng bảo vệ có bàn trực, tủ hồ sơ và kệ nước riêng. Mã ngắn trên mô hình trùng mã cạnh tên đầy đủ trong danh sách. Nhấn icon hoặc dùng Tab rồi Enter/Space để bật/tắt; ở chế độ tự động các nút được khóa và phản ánh thiết bị do kịch bản chọn. Home dùng cùng tọa độ ở dạng rút gọn.

## Thông số và lưu trữ

Thiết bị dùng model tham chiếu thực tế. [DEVICE_REFERENCES.md](DEVICE_REFERENCES.md) phân biệt dòng định mức, giới hạn AC đầu vào, giá trị quy đổi và điều kiện của từng nguồn. Mô hình giữ dòng tham chiếu cố định khi bật; không mô phỏng dòng khởi động, thay đổi tốc độ, thermostat hay mức tải xử lý.

An toàn khi I < ngưỡng cảnh báo; cảnh báo khi ngưỡng cảnh báo ≤ I < ngưỡng nguy hiểm; nguy hiểm khi I ≥ ngưỡng nguy hiểm.

Cấu hình và công tắc lưu trong `data/rooms.sqlite3`. Khi mở cơ sở dữ liệu phiên bản cũ, ứng dụng tự chuyển một lần sang đơn vị A. Mức mặc định được cập nhật theo bảng tham chiếu; mức đã tự chỉnh được giữ tương đương ở 220 V. Ngưỡng và công tắc được bảo toàn. Bản sao trước chuyển đổi: `data/rooms_before_current_a_20261101.sqlite3`.

Lịch sử lấy mẫu nằm trong bộ nhớ máy chủ và bắt đầu phiên mới khi nhấn Khởi động. Dùng một tiến trình máy chủ cho bản đồ án. Thư viện giao diện nằm tại `static/vendor`, không cần CDN.

Trạng thái thiết bị của kịch bản tự động chỉ nằm trong RAM, không ghi SQLite ở mỗi giây. Mỗi thiết bị có dòng cố định nên một tải ngẫu nhiên bất kỳ có thể không đạt chính xác: ví dụ mục tiêu 15 A ở phòng học có thể chọn hai điều hòa 7,9 A, hiển thị đúng 15,8 A và 2 thiết bị bật. Home, chi tiết phòng và phần phụ tải trong báo cáo nhận cùng bản chụp từ backend. Khi người dùng sửa Settings, kịch bản dùng các giá trị mới thay vì mặc định trong ví dụ này.

Đổi đường dẫn dữ liệu bằng `ROOM_DATABASE`, đổi cổng bằng `PORT`. Tắt Telegram khi chạy thử:

```powershell
$env:TELEGRAM_ENABLED = '0'
.\run.ps1
```

Thông tin Telegram được đọc từ biến môi trường hoặc file `.env` nằm cạnh `app.py`. Trên máy mới, sao chép `.env.example` thành `.env`, điền `TELEGRAM_TOKEN`, `TELEGRAM_CHAT_ID` và đặt `TELEGRAM_ENABLED=1` khi cần gửi thông báo. Không đưa `.env` lên Git. Biến môi trường có sẵn được ưu tiên hơn file `.env`.

Hướng dẫn đưa web lên Internet, giữ SQLite và tự triển khai khi push: [RENDER.md](../RENDER.md).

`simulate_sensor.py` là bộ phát MQTT riêng của bản gốc; web hiện không nhận dữ liệu từ script này.

## Kiểm thử

```powershell
.\.venv\Scripts\python.exe -m unittest discover -s tests -v
node --check static/js/app.js
node --check static/js/room-model.js
node --test tests/frontend.test.cjs tests/room-model.test.cjs
```

Các bài kiểm thử dùng SQLite tạm và tắt Telegram. Xem kết quả tại `VERIFICATION.md`. Bản gốc và các mốc nâng cấp có trong các file `backup_*.zip`.

`tools/check_room_ui.cjs` dành cho kiểm thử giao diện thật khi có Playwright và trình duyệt tương ứng. Có thể đặt `PLAYWRIGHT_PACKAGE` thành đường dẫn module Playwright đã cài. Script tự khởi động backend tại cổng loopback trống, dùng SQLite mới trong `test-results`, tắt Telegram và tạo profile trình duyệt tạm; kiểm tra bốn viewport, công tắc, bàn phím, Bật tất cả, hai client, chế độ tự động và xác nhận/hủy reset. Không truyền script này vào máy chủ hoặc database đang sử dụng.
