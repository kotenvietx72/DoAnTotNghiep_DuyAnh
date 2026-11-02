# Kết quả kiểm tra

## Triển khai bố cục ba phòng đã duyệt — 02/11/2026

- Đã đưa bộ bố trí đã duyệt vào `static/js/room-model.js`, dùng chung cho Home và chi tiết. Giữ đủ 33 thiết bị và ID; mã ngắn trên sơ đồ có mã tương ứng cạnh tên đầy đủ trong danh sách.
- Phòng học: bàn giáo viên phía bảng, quạt giữa các dãy, Đ3/Đ6 dịch phải. Kí túc xá: cửa/lối đi ở trục giữa, giường và các cặp đèn/quạt/bàn đối xứng. Phòng bảo vệ: bàn trực hướng cửa sổ, quạt ngoài tủ, khu nước riêng. Vùng cửa chính không giao bàn, giường, ghế hoặc tủ.
- Mô hình dùng nút HTML và lớp icon độc lập kích thước sơ đồ. Đã kiểm tra click, Enter và Space: đúng một POST mỗi lần, cập nhật đồng thời công tắc danh sách và client thứ hai. Nút đang chờ hoặc không khả dụng bị khóa; màu thiết bị theo state backend.
- **40/40 unittest Python và 8/8 kiểm thử JavaScript đạt**; hai file JavaScript và diff vượt kiểm tra cú pháp/whitespace. CI chạy cả test controller và renderer.
- **E2E giao diện thật đạt** bằng `tools/check_room_ui.cjs`: 12 trang chi tiết ở 1440/1024/390/320 px và Home ở bốn viewport. Đủ 33 icon, không có vùng bấm giao nhau, mỗi nút ít nhất 44 px, không tràn ngang; cửa không giao nội thất, đèn kí túc xá thẳng tâm giường và lối đi ở giữa. Bật tất cả, Socket.IO hai client, start/stop kịch bản và xác nhận/hủy reset Settings đạt; không có lỗi JavaScript.
- Đã mở ảnh chụp desktop/mobile để kiểm tra trực quan; nhãn khu tắm/khu nước xuống dòng trong vùng riêng ở màn hình hẹp. Bằng chứng: `A:\DoAnTotNghiep_DuyAnh_docs\evidence\web-room-layout\` và `report.json`. Đây là ảnh web thật sau khi sửa code, khác ảnh thiết kế trong `design/`.
- Backend, SQLite và profile Edge đều được tạo riêng cho test; Telegram tắt. Script đóng các process thử của nó sau khi chạy. Không dùng tab hoặc dữ liệu người dùng. PDF không nằm trong phạm vi thay đổi này và chưa kiểm tra trực quan lại.
- Phần hạn chế truy cập trình duyệt ở mốc F21–F23 bên dưới là lịch sử; đợt này đã kiểm tra được UI bằng browser headless với profile mới. Không sửa Android nên không áp dụng Gradle cho thay đổi web.

## F21–F23 — 02/11/2026

- Đã triển khai bật tất cả riêng từng phòng, reset thông số mặc định có xác nhận và đồng bộ thiết bị với số đo trong kịch bản tự động.
- **40/40 unittest Python đạt**, gồm 29 bài hiện có và 11 bài hồi quy mới. Đã kiểm tra ba phòng qua 45 mẫu có seed: tổng dòng/số thiết bị/trạng thái cùng khớp; chuyển về thủ công giữ nguyên trạng thái RAM và SQLite.
- Kiểm thử API xác nhận thao tác hàng loạt chỉ ghi một lần, lặp lệnh không cộng trùng, các phòng độc lập; lỗi SQLite hoàn tác RAM và không publish hoặc ghi nhật ký thành công. Reset khôi phục đúng mặc định, giữ công tắc và lịch sử, làm mới tổ hợp mô phỏng mà không reset pha. Thời lượng trước/sau đổi tải được chia đúng.
- Hai Socket.IO client nhận cùng state/revision của API mới; đọc state/báo cáo khi dừng không làm random lại. Kiểm thử chọn tổ hợp đối chiếu vét cạn với ngưỡng biên, mức không thể đạt, tổ hợp bằng tải, thiết bị 0 A và đổi cấu hình.
- **5/5 kiểm thử controller JavaScript đạt** bằng Node VM với DOM/socket/HTTP giả lập: xác nhận/hủy reset, điền lại form sau thành công, giữ bản nháp khi tab khác thay cấu hình, đồng bộ sau mất phản hồi, một lệnh bật hàng loạt và khóa điều khiển khi đang gửi/mất kết nối/ở chế độ tự động. Đây là kiểm thử logic, không thay thế kiểm tra layout thật.
- `node --check` cho hai file JavaScript và `git diff --check` đạt. CI được bổ sung lệnh chạy test controller.
- Dùng `.venv/Scripts/python.exe`; TEMP/TMP đặt trong `test-results/tmp` cho SQLite tạm. Không thao tác database người dùng, không gửi Telegram thật. Bản thử HTTP dùng `127.0.0.1:5062` và SQLite riêng trong `test-results`.
- **Chưa xác minh trực quan giao diện desktop/mobile hoặc PDF mới**: trình duyệt tích hợp không truy cập được địa chỉ cục bộ; Computer Use dừng vì không xác minh được URL Edge. Không đọc Google Sheets đang mở hoặc thao tác tiếp trên cửa sổ đó.
- Thay đổi thuộc web Flask; không sửa Android nên không chạy Gradle assembleDebug/lint.

Các phần dưới là bằng chứng của mốc **01/11/2026**, giữ để tham chiếu lịch sử.

## Chuẩn bị GitHub và Render

- **29/29 bài kiểm thử thành công**, gồm 24 bài nghiệp vụ hiện có và 5 bài bảo mật Telegram mới.
- Telegram chỉ đọc token/chat ID từ biến môi trường hoặc `.env` cục bộ. Thiếu cấu hình hoặc tắt Telegram không gửi request; lỗi request chỉ ghi tên loại lỗi, không ghi URL/token/chat ID.
- Kiểm thử khởi động trong môi trường không có `.env` hoặc thông tin Telegram: `/api/state` trả HTTP 200 với SQLite tạm.
- Hai file JavaScript vượt qua `node --check`.
- Đã quét nội dung chuẩn bị commit, bao gồm dữ liệu bên trong file Excel mẫu: không chứa token/chat ID thật hoặc các mẫu secret được kiểm tra. `.env`, virtualenv, SQLite và ZIP sao lưu được loại khỏi Git.
- Bộ kiểm thử trên máy này dùng thư mục tạm trong `test-results/tmp` vì sandbox Windows hạn chế SQLite ở thư mục Temp mặc định; không thay đổi SQLite thật.
- Cấu hình Render đã đổi sang `plan: free`, không có persistent disk hoặc database trả phí; dùng một Gunicorn worker với threading và nhận `PORT` từ Render. SQLite tại `data/rooms.sqlite3` là dữ liệu tạm trên Render Free, không giữ qua các lần ngủ/khởi động lại/triển khai lại.
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
