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
2. Nhấn thiết bị trên sơ đồ hoặc công tắc. Mỗi thiết bị có dòng điện tham chiếu riêng, xem [bảng model và nguồn](DEVICE_REFERENCES.md).
3. Dòng điện phòng bằng tổng A của thiết bị đang bật. Tắt hết: **0 A**; điện áp nguồn vẫn là **220 V**.
4. Ô **Tổng dòng điện** cộng dòng của ba nhánh phòng trong mô hình một pha dùng chung nguồn. Điện áp các nhánh không cộng với nhau.
5. **Cài đặt** cho phép chỉnh dòng thiết bị và hai ngưỡng cảnh báo/nguy hiểm, đều bằng A. Lưu để áp dụng ngay.
6. **Khởi động lấy mẫu** để ghi biểu đồ và thời lượng. **Dừng** ngừng ghi lịch sử; công tắc vẫn hoạt động.
7. **Kịch bản tự động** giữ mô phỏng cũ; dừng lấy mẫu trước khi chuyển. Số đo kịch bản độc lập với công tắc.
8. **Phân tích nội bộ** đọc Excel/CSV ba cột: thời gian, điện áp, dòng điện. Chọn phòng hoặc cấu hình một pha gốc 25/40 A, xem biểu đồ và xuất PDF.

## Thông số và lưu trữ

Thiết bị dùng model tham chiếu thực tế. [DEVICE_REFERENCES.md](DEVICE_REFERENCES.md) phân biệt dòng định mức, giới hạn AC đầu vào, giá trị quy đổi và điều kiện của từng nguồn. Mô hình giữ dòng tham chiếu cố định khi bật; không mô phỏng dòng khởi động, thay đổi tốc độ, thermostat hay mức tải xử lý.

An toàn khi I < ngưỡng cảnh báo; cảnh báo khi ngưỡng cảnh báo ≤ I < ngưỡng nguy hiểm; nguy hiểm khi I ≥ ngưỡng nguy hiểm.

Cấu hình và công tắc lưu trong `data/rooms.sqlite3`. Khi mở cơ sở dữ liệu phiên bản cũ, ứng dụng tự chuyển một lần sang đơn vị A. Mức mặc định được cập nhật theo bảng tham chiếu; mức đã tự chỉnh được giữ tương đương ở 220 V. Ngưỡng và công tắc được bảo toàn. Bản sao trước chuyển đổi: `data/rooms_before_current_a_20261101.sqlite3`.

Lịch sử lấy mẫu nằm trong bộ nhớ máy chủ và bắt đầu phiên mới khi nhấn Khởi động. Dùng một tiến trình máy chủ cho bản đồ án. Thư viện giao diện nằm tại `static/vendor`, không cần CDN.

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
```

Các bài kiểm thử dùng SQLite tạm và tắt Telegram. Xem kết quả tại `VERIFICATION.md`. Bản gốc và các mốc nâng cấp có trong các file `backup_*.zip`.
