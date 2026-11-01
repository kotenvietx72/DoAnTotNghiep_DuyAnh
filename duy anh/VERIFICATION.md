# Kết quả kiểm tra — 01/11/2026

## Chuẩn bị GitHub và Render

- **29/29 bài kiểm thử thành công**, gồm 24 bài nghiệp vụ hiện có và 5 bài bảo mật Telegram mới.
- Telegram chỉ đọc token/chat ID từ biến môi trường hoặc `.env` cục bộ. Thiếu cấu hình hoặc tắt Telegram không gửi request; lỗi request chỉ ghi tên loại lỗi, không ghi URL/token/chat ID.
- Kiểm thử khởi động trong môi trường không có `.env` hoặc thông tin Telegram: `/api/state` trả HTTP 200 với SQLite tạm.
- Hai file JavaScript vượt qua `node --check`.
- Đã quét nội dung chuẩn bị commit, bao gồm dữ liệu bên trong file Excel mẫu: không chứa token/chat ID thật hoặc các mẫu secret được kiểm tra. `.env`, virtualenv, SQLite và ZIP sao lưu được loại khỏi Git.
- Bộ kiểm thử trên máy này dùng thư mục tạm trong `test-results/tmp` vì sandbox Windows hạn chế SQLite ở thư mục Temp mặc định; không thay đổi SQLite thật.
- Cấu hình Render dùng một Gunicorn worker với threading, nhận `PORT` từ Render và đặt SQLite tại `/var/data/rooms.sqlite3` trên persistent disk.
- GitHub Actions được cấu hình để chạy kiểm thử, kiểm tra JavaScript và thử khởi động Gunicorn trên Linux sau khi push. Chưa thao tác triển khai dịch vụ Render.

## Kiểm thử tự động

**24/24 bài kiểm thử thành công** với `.venv\Scripts\python.exe -m unittest discover -s tests -v`.

- Tất cả thiết bị tắt: dòng phòng chính xác 0 A, điện áp nguồn vẫn 220 V; các phòng độc lập.
- Dòng phòng bằng tổng dòng thiết bị bật. Gửi lại trạng thái Bật không cộng trùng.
- Tổng dòng hệ thống cộng dòng ba phòng, không cộng điện áp của các phòng.
- Ngưỡng cảnh báo/nguy hiểm bao gồm đúng giá trị bằng ngưỡng; phép cộng thập phân không làm bỏ qua ngưỡng.
- Thiết bị 0 A, số âm, NaN, vô hạn, bool và kiểu dữ liệu sai được xử lý đúng.
- Lưu cấu hình không hợp lệ bị từ chối toàn bộ; chỉnh dòng thiết bị đang bật cập nhật tổng ngay.
- SQLite phục hồi dòng thiết bị, ngưỡng và trạng thái công tắc sau khởi động lại.
- Dữ liệu cũ chuyển sang A đúng một lần: mặc định cũ nhận dòng tham chiếu mới, mức tự chỉnh giữ giá trị tương đương; giữ ngưỡng và công tắc.
- Các trang Flask, API, tài nguyên tĩnh và trang phòng không tồn tại hoạt động đúng.
- Hai Socket.IO client nhận cùng trạng thái; client kết nối sau không reset client đang mở.
- Bắt đầu/dừng/bắt đầu nhanh chỉ có một luồng lấy mẫu; thời lượng trạng thái được cộng đúng.
- Chế độ theo thiết bị và kịch bản tự động tách biệt, giữ công tắc đã lưu.
- Đọc CSV/XLSX, tải file mẫu, từ chối dữ liệu sai và giữ cấu hình phân tích một pha gốc 25/40 A.

Hai file JavaScript vượt qua `node --check`; `app.py`, `room_service.py` và `device_references.py` vượt qua kiểm tra biên dịch Python. Dự án web Flask không có Gradle nên không áp dụng assembleDebug/lint Android.

## Kiểm tra trên trình duyệt

- Desktop 1440 px và điện thoại 390 px: tổng quan và chi tiết phòng không tràn ngang.
- Ba mô hình SVG tự vẽ 2D từ trên xuống; không có ảnh ngoài, phép xoay/skew/perspective hoặc nút quay lại.
- Nội dung giao diện chỉ hiển thị dòng điện A và điện áp V. Thẻ tổng quan dùng “Tổng dòng điện”; mỗi phòng có hai cột Dòng điện / Điện áp.
- Phòng học: bật đèn 0,095 A rồi quạt 0,352 A → 0,447 A. Tắt cả hai → 0 A, điện áp giữ 220 V.
- Bật/tắt hoạt động qua công tắc và thiết bị trên mô hình; dữ liệu cập nhật ngay khi chưa lấy mẫu.
- Cài đặt có đủ 33 ô dòng thiết bị, lưu thành công và giữ các giá trị đã lưu.
- Khởi động/dừng lấy mẫu hoạt động; không ghi nhận lỗi/cảnh báo JavaScript trong lượt kiểm tra.
- Bảng xuất báo cáo được đổi sang A/V. Đã kích hoạt chức năng xuất sau thay đổi này; chưa kiểm tra trực quan lại file PDF mới tải về. Quy trình tạo PDF đã được xuất và render kiểm tra ở lượt trước.

Ảnh giao diện mới: `test-results/current-voltage-dashboard.jpg`, `current-voltage-classroom.jpg`, `current-voltage-dormitory.jpg`, `current-voltage-security.jpg`, `current-voltage-mobile.jpg`.

Các công tắc bật do kiểm thử đã được trả về trạng thái trước kiểm thử. Giữ nguyên sáu thiết bị người dùng đang bật ở phòng bảo vệ; dữ liệu đã chuyển đơn vị có tổng tham chiếu 12,502 A tại 220 V.

## Phạm vi

Thông số tham chiếu và nguồn hãng được ghi trong `DEVICE_REFERENCES.md`. Một số là giới hạn đầu vào hoặc giá trị quy đổi/ước tính, không phải dòng đo tức thời. Mô hình ON/OFF cộng giá trị tham chiếu cố định và coi Tắt là ngắt khỏi nhánh.

Telegram tắt trong lúc kiểm thử để không gửi tin thật. Không chạy bộ phát MQTT ra broker bên ngoài. Tích hợp gốc được giữ. Lịch sử lấy mẫu chạy trong tiến trình Flask; cấu hình và công tắc lưu SQLite.
