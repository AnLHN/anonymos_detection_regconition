# User Admin Interface Refresh Plan

## Mục tiêu

Làm lại bảng quản trị người dùng theo hướng production, đồng bộ với giao diện admin hiện tại, không bê nguyên layout ảnh mẫu vào như một block tách biệt.

## Phase 1 - Bảng người dùng native

Trạng thái: Done

- Đổi bảng users thành bảng vận hành dày thông tin: avatar chữ cái, username/email, vai trò, trạng thái, hoạt động gần nhất, hành động.
- Giữ tone màu sáng xanh nhạt và border radius thấp đang dùng trong app.
- Hành động nguy hiểm dùng nút nhỏ, không chiếm diện tích hàng.

## Phase 2 - Popup quản lý vai trò

Trạng thái: Done

- Click vào role pill sẽ mở popup quản lý vai trò.
- Vì backend hiện dùng role cấp số `0/1/5/9`, modal sẽ chỉnh một cấp quyền hiện có, không giả lập multi-role.
- Modal có mô tả ngắn quyền hiện tại và lưu trực tiếp qua API `PATCH /users/{username}`.

## Phase 3 - Popup hoạt động/lịch sử đăng nhập

Trạng thái: Done

- Click vào hoạt động gần nhất mở popup lịch sử.
- Backend ghi login/logout thật vào `user_login_events`.
- UI đọc endpoint `/users/{username}/login-history` để hiển thị thời gian, hành động, IP, thiết bị và VPN flag.
- IP location/VPN để `N/A` hoặc `Chưa xác định` khi chưa có nguồn enrich như Nginx/VPN gateway hoặc GeoIP nội bộ.

## Phase 4 - Sidebar account refresh

Trạng thái: Done

- Cập nhật cụm account góc trái thành mini profile có popup.
- Popup account tạm thời chỉ giữ `Đăng xuất` theo yêu cầu.
- Bỏ nút `System OK` khỏi topbar.

## Phase 5 - Kiểm thử

Trạng thái: Done

- Chạy typecheck frontend.
- Kiểm tra CSS không làm vỡ sidebar ở zoom 100%.

## Phase 6 - Login history hardening

Trạng thái: Done

- Backend tự tạo bảng `user_login_events` khi ghi/đọc login history để tránh lỗi khi DB đang chạy chưa được migrate.
- Nginx production đã có access log format và vẫn forward `X-Real-IP`, `X-Forwarded-For`.
- Local dev qua `./start.sh` có thể không đi qua Nginx production, nên IP/VPN enrich vẫn phụ thuộc đường truy cập thực tế.
