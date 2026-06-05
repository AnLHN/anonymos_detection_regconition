# System Camera & Monitoring Consolidation Plan

## Mục tiêu

Đồng bộ lại trải nghiệm vận hành cho admin:

- Bộ lọc camera trên dashboard phải lấy từ danh sách camera thực tế, không gán cứng.
- Gộp `System Health` và `Monitoring` thành một trang quan sát hệ thống duy nhất.
- Bỏ Grafana khỏi giao diện native mặc định, chỉ dùng Prometheus/backend analytics để hiển thị thông tin cần thiết.
- Làm rõ giới hạn của các tín hiệu security: đây là chỉ báo vận hành, không phải IDS/WAF/VPN gateway đầy đủ.

## Phase 1 - Camera filter động

Trạng thái: Done

- Xóa danh sách camera hard-code trong `LiveMonitor`.
- Dropdown `Camera` tự sinh option từ danh sách camera RTSP đang active.
- Nếu camera đang chọn bị xóa hoặc tắt active, UI tự quay về `Tất cả camera`.

## Phase 2 - Gộp System Health và Monitoring

Trạng thái: Done

- Sidebar chỉ còn một mục `System Monitor`.
- Route `/system` dùng bảng analytics native.
- Route `/system/monitoring` redirect về `/system` để không gãy link cũ.
- Topbar health popover trỏ về `System Monitor`.

## Phase 3 - Bỏ Grafana khỏi UI mặc định

Trạng thái: Done

- Native System Monitor không hiển thị chip Grafana.
- Backend analytics không đưa Grafana vào danh sách service mặc định.
- Grafana vẫn còn trong Docker Compose dưới profile tùy chọn, không còn là UI admin chính.

## Phase 4 - Security signal minh bạch

Trạng thái: Done

- UI thêm ghi chú: tín hiệu security hiện tại là heuristic từ Prometheus/backend.
- VPN/firewall hiển thị unknown khi chưa ingest access log từ Nginx/VPN gateway.
- Backend message đã nêu rõ Nginx production gateway có tồn tại, nhưng analytics chưa đọc log Nginx/VPN.

## Phase 5 - Kiểm thử

Trạng thái: Done

- `npm.cmd run typecheck --prefix frontend`
- `python -m compileall backend`
