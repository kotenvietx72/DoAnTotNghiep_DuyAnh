# Triển khai lên Render Free

Repository: https://github.com/kotenvietx72/DoAnTotNghiep_DuyAnh

## Cách nhanh: Blueprint

1. Đăng nhập [Render](https://dashboard.render.com/) bằng tài khoản của chủ repository, kết nối GitHub.
2. Chọn **New → Blueprint**, chọn repository này và nhánh `main`.
3. Render đọc `render.yaml` ở gốc repository. Kiểm tra dịch vụ có **Instance Type: Free**, không có disk hoặc database trả phí, rồi tạo dịch vụ.
4. Chờ dịch vụ báo **Live**, mở địa chỉ HTTPS `onrender.com` Render cấp và chia sẻ.

Blueprint hiện dùng **`plan: free`**, không tạo persistent disk hoặc database trả phí. Blueprint là cách khai báo cấu hình; chi phí phụ thuộc các tài nguyên được tạo. Dịch vụ này miễn phí trong hạn mức của [Render Free](https://render.com/docs/free). Sau lần thiết lập này, mỗi lần push vào `main`, Render tự build và triển khai bản mới.

Nếu đã tạo dịch vụ hoặc disk trả phí từ cấu hình cũ, kiểm tra các tài nguyên đó trong Dashboard và sao lưu dữ liệu cần giữ trước khi tự dừng/xóa hoặc chuyển gói. Chỉ cập nhật YAML không đảm bảo tài nguyên trả phí cũ đã được xóa.

## Cách nhập cấu hình bằng tay: Web Service

Chọn **New → Web Service → Git Provider**, kết nối GitHub và chọn repository. Cần kết nối tài khoản GitHub để có Auto Deploy; cách dán URL public đơn thuần không bật tính năng này.

| Mục | Giá trị |
|---|---|
| Branch | `main` |
| Region | Singapore |
| Language | Python 3 |
| Instance Type | Free |
| Root Directory | `duy anh` |
| Build Command | `pip install -r requirements.txt` |
| Start Command | `gunicorn --worker-class gthread --workers 1 --threads 20 --bind 0.0.0.0:$PORT app:app` |
| Auto-Deploy | On Commit |
| Health Check Path | `/api/state` |
| Instances | 1 |

Đặt các biến tại **Environment**:

| Biến | Giá trị |
|---|---|
| `PYTHON_VERSION` | `3.12.14` |
| `PYTHON_DOTENV_DISABLED` | `1` |
| `ROOM_DATABASE` | `data/rooms.sqlite3` |
| `TELEGRAM_ENABLED` | `0` khi chưa cấu hình Telegram |

Không ghi đè biến `PORT` do Render cấp. Gói Free không hỗ trợ persistent disk; cấu hình này lưu SQLite trong thư mục tạm thời của dịch vụ.

## Giới hạn của Free

- Sau **15 phút không nhận truy cập**, dịch vụ ngủ. Lượt truy cập tiếp theo đánh thức web, thường mất khoảng **một phút**.
- Dữ liệu SQLite, gồm công tắc và cấu hình đã chỉnh trên web, **mất khi dịch vụ ngủ, khởi động lại hoặc triển khai bản mới**. Khi mở lại, ứng dụng tạo cấu hình mặc định. Lịch sử lấy mẫu trong RAM cũng bắt đầu lại.
- Workspace có **750 giờ dịch vụ Free mỗi tháng**, dùng chung cho các dịch vụ Free đang chạy. Băng thông và thời gian build cũng có hạn mức; xem **Usage / Billing** để theo dõi.
- Phù hợp chia sẻ và trình diễn đồ án khi chấp nhận dữ liệu tạm. Giữ dữ liệu lâu dài cần bổ sung nơi lưu trữ bên ngoài; bản hiện tại chưa có tích hợp này.

## Telegram

Token và chat ID thật không nằm trong Git. Để bật thông báo, thêm trực tiếp tại **Render → Environment**:

- `TELEGRAM_TOKEN`: token bot của anh.
- `TELEGRAM_CHAT_ID`: ID nơi nhận thông báo.
- `TELEGRAM_ENABLED`: `1`.

Không điền token vào README, `render.yaml`, GitHub Actions hoặc ảnh chụp công khai. Nếu token từng được đăng công khai trước đây, dùng `@BotFather` để thu hồi và cấp token mới; xóa khỏi code không vô hiệu hóa token cũ.

Trên máy Windows, ứng dụng tự đọc `.env` nằm cạnh `app.py`; biến môi trường đã có được ưu tiên. Máy mới có thể sao chép `.env.example` thành `.env` và điền cấu hình. Token trên máy hiện tại đã được chuyển sang `.env`, không cần chép lại vào code.

## Cập nhật web lần sau

Chạy từ thư mục gốc repository:

```powershell
git status
git add .
git commit -m "Cap nhat giao dien va tinh nang"
git push
```

Render tự cập nhật khi push vào nhánh `main`. Nếu build thất bại, xem **Logs / Events** trên Render; phiên bản cũ tiếp tục phục vụ khi build mới chưa thành công.

## Dữ liệu và phạm vi bản demo

- SQLite trên server là dữ liệu riêng, không tự sao chép từ SQLite trên máy Windows. Lần triển khai đầu tạo cấu hình mặc định.
- Bản Free dùng SQLite tạm thời. Công tắc, cấu hình và lịch sử lấy mẫu trên server không được giữ qua các lần khởi động lại.
- Chỉ chạy **một instance, một Gunicorn worker** vì trạng thái mô phỏng và Socket.IO đang dùng chung bộ nhớ trong tiến trình.
- Khi triển khai lại hoặc đánh thức dịch vụ, kết nối Socket.IO sẽ phải kết nối lại.
- Bản demo hiện dùng chung công tắc và cài đặt cho mọi khách truy cập, chưa có đăng nhập hoặc phân quyền chỉ xem.

Nguồn: [Render Free](https://render.com/docs/free), [Render Blueprint](https://render.com/docs/blueprint-spec), [Render Web Services](https://render.com/docs/web-services), [Auto Deploy](https://render.com/docs/deploys), [Flask-SocketIO Deployment](https://flask-socketio.readthedocs.io/en/latest/deployment.html).
