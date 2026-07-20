# Frontend UI/UX Improvement TODO

## 🎯 Mục tiêu
Nâng giao diện từ khoảng **8.8–9.2/10** lên **9.5+/10** theo hướng Enterprise Dashboard.

---

# 🔴 High Priority

## 1. Dashboard
- [ ] Giảm khoảng trống ở Dashboard.
- [ ] Bổ sung các thống kê nhanh:
  - Camera Online
  - Unknown Today
  - Known Today
  - FPS
  - GPU Usage
  - Detection/Hour

---

## 2. Camera Management
- [ ] Hiển thị thêm thông tin trên mỗi camera:
  - FPS
  - Resolution
  - Latency
  - Worker
  - Last Seen
  - Reconnect Status

---

## 3. Settings Page
- [ ] Chia các nhóm thiết lập bằng Accordion/Collapse:
  - General
  - ROI
  - Unknown Detection
  - Gate
  - Schedule
- [ ] Giảm số lượng input hiển thị cùng lúc.

---

## 4. Employee Page
- [ ] Thay layout Form + List bằng:
  - Tab (Danh sách / Thêm nhân viên)
  - hoặc Drawer/Modal để thêm nhân viên.
- [ ] Giúp danh sách dễ quản lý khi dữ liệu lớn.

---

## 5. Alert Detail Modal
- [ ] Chuyển sang layout 2 cột:
  - Trái: Hình ảnh
  - Phải: Thông tin
- [ ] Hạn chế phải cuộn (scroll).

---

# 🟡 Medium Priority

## 6. Sidebar
- [ ] Giảm chiều rộng còn khoảng **240px** để tăng không gian hiển thị.

---

## 7. Header
- [ ] Giảm chiều cao Header (~90px).
- [ ] Tăng diện tích cho nội dung chính.

---

## 8. Alert List
- [ ] Giảm chiều cao Alert Card (~80–90px).
- [ ] Hiển thị được nhiều cảnh báo hơn trên màn hình.

---

## 9. User Management
- [ ] Tăng khoảng cách giữa nút **Sửa** và **Khóa/Xóa**.
- [ ] Tránh thao tác nhầm.

---

## 10. Typography
- [ ] Chuẩn hóa Font Weight:
  - Title: 700
  - Subtitle: 600
  - Body: 400

---

## 11. Border & Background
- [ ] Giảm độ đậm của Grid Background.
- [ ] Giảm Border xuống 1px (#E7EDF5).
- [ ] Tăng cảm giác hiện đại và cao cấp.

---

# 🟢 Low Priority

## 12. Hover & Animation
- [ ] Thêm Hover cho:
  - Card
  - Camera
  - Alert
  - Button
- [ ] Thêm Shadow/Lift Effect.
- [ ] Thêm Transition mượt cho:
  - Modal
  - Sidebar
  - Filter
  - Notification

---

## 13. Login Page
- [ ] Thêm Background Gradient.
- [ ] Thêm AI Particle hoặc Animation nhẹ.
- [ ] Giảm cảm giác trống trải.

---

## 14. Loading State
- [ ] Thêm Skeleton Loading.
- [ ] Thêm Spinner phù hợp.

---

## 15. Toast Notification
- [ ] Hiển thị thông báo:
  - Save Success
  - Update Success
  - Camera Reload
  - Rule Updated

---

# ⭐ Nice to Have

- [ ] Dark Mode.
- [ ] Camera Grid (2x2, 3x3, 4x4, Fullscreen).
- [ ] Alert Timeline.
- [ ] Heatmap khu vực phát hiện người lạ.
- [ ] AI Confidence (%) trên kết quả nhận diện.
- [ ] Dashboard Mini Analytics.

---

# Kết luận

### Điểm mạnh (Giữ nguyên)
- Layout rõ ràng.
- Design System đồng nhất.
- Màu sắc phù hợp hệ thống AI/Security.
- Whitespace tốt.
- Luồng nghiệp vụ sát với hệ thống Enterprise thực tế.

### Cần cải thiện
- Tăng mật độ thông tin ở Dashboard và Camera.
- Tối ưu UX cho các trang nhiều dữ liệu (Settings, Employee, Alert).
- Bổ sung micro-interactions (hover, animation, loading).
- Chuẩn hóa typography và spacing.
- Giảm khoảng trống chưa cần thiết.
- Hoàn thiện các trạng thái (loading, notification, live status).

> Sau khi hoàn thành các mục trên, giao diện sẽ đạt chất lượng gần với các Enterprise Dashboard hiện đại và nâng tổng trải nghiệm UI/UX lên khoảng **9.5+/10**.
