# Ke hoach chuyen thong bao System Health khoi Dashboard

## Van de hien tai

Dong thong bao dang hien ngay tren Dashboard:

```text
System ok | Postgres true | Qdrant true | Redis true | Workers 0/3
```

No mang tinh ky thuat noi bo, khong phai thong tin chinh cua nguoi van hanh camera. Khi dat o dau Dashboard, no lam giao dien bi vuong, tao cam giac he thong dang "debug" va tranh su chu y voi noi dung quan trong hon la luong camera.

## Dinh huong de xuat

Khong hien thong bao health/status truc tiep tren Dashboard. Dashboard chi nen tap trung vao:

- Luong camera.
- Trang thai camera neu can, vi du online/offline tren tung camera.
- Canh bao van hanh lien quan truc tiep den camera.

Thong tin he thong nhu database, Redis, Qdrant, workers nen dua vao khu vuc admin hoac cai dat, vi day la thong tin danh cho nguoi quan tri ky thuat.

## Vi tri hien thi phu hop

### Lua chon 1 - Admin Settings > System Health

Day la lua chon nen uu tien.

Dat mot tab rieng trong giao dien cai dat admin:

```text
Admin Settings
- General
- Users & Roles
- Camera Config
- Alert Rules
- System Health
- Audit Logs
```

Trong tab `System Health`, hien thi trang thai chi tiet:

- System: OK / Warning / Error
- Postgres: Connected / Disconnected
- Qdrant: Connected / Disconnected
- Redis: Connected / Disconnected
- Workers: 0/3, 1/3, 3/3
- Last checked time
- Nut refresh thu cong

Ly do phu hop:

- Dung ngu canh: day la thong tin quan tri he thong.
- Khong lam roi Dashboard.
- Admin van de dang kiem tra khi can debug hoac bao tri.

### Lua chon 2 - Admin Sidebar co muc "System Status"

Neu muon truy cap nhanh hon, co the them muc rieng trong sidebar admin:

```text
Admin
- Dashboard
- Cameras
- Alerts
- Users
- System Status
- Settings
```

Trang `System Status` hien chi tiet hon `System Health`, co the them:

- Service uptime.
- Worker queue.
- API status.
- Storage status.
- Recent system errors.

Ly do phu hop:

- Tot cho admin/super admin.
- Tach bach ro voi Dashboard camera.
- De mo rong thanh man hinh giam sat ky thuat rieng.

### Lua chon 3 - Chi hien indicator nho trong Admin Header

Neu van muon admin nhin thay nhanh tinh trang he thong, co the hien mot indicator rat gon trong header admin:

```text
[Cham xanh] System OK
```

Khi bam vao moi mo popover chi tiet:

```text
System OK
Postgres Connected
Qdrant Connected
Redis Connected
Workers 0/3
Last checked 14:32

[Open System Health]
```

Luu y:

- Chi hien trong khu vuc admin, khong hien tren Dashboard camera.
- Neu moi thu OK thi indicator nen that gon.
- Chi khi co loi nghiem trong moi can noi bat.

## Huong nen chon

Nen ket hop `Lua chon 1` va `Lua chon 3`:

- Tao tab `System Health` trong `Admin Settings` de xem chi tiet.
- Trong Admin Header chi hien mot cham trang thai nho cho admin.
- Dashboard camera khong hien dong health/status nua.

## Cach hien thi de khong gay vuong

### Khi he thong binh thuong

Khong can hien thong bao tren Dashboard.

Trong admin header:

```text
System OK
```

Chi la mot badge nho, mau xanh, khong chiem nhieu dien tich.

### Khi co canh bao ky thuat

Trong admin header:

```text
System Warning
```

Bam vao xem popover tom tat:

```text
System Warning
Workers 0/3 inactive
Redis Connected
Postgres Connected
Qdrant Connected

[View details]
```

### Khi co loi nghiem trong

Chi luc nay moi can hien notification cho admin/super admin:

```text
System Error
Postgres disconnected

[Open System Health]
```

Khong hien cho user van hanh camera neu user do khong co quyen admin.

## Phase 1 - Go khoi Dashboard

### Muc tieu

Loai bo dong health/status khoi dau trang Dashboard.

### Cong viec

- Tim component dang render dong `System ok | Postgres true | Qdrant true | Redis true | Workers 0/3`.
- Khong render component nay trong Dashboard camera.
- Dam bao phan tieu de Dashboard va camera grid khong bi doi layout xau.

### Ket qua mong doi

Dashboard mo len chi thay noi dung lien quan den camera va van hanh camera.

## Phase 2 - Tao trang Admin Settings > System Health

### Muc tieu

Chuyen thong tin health/status vao dung khu vuc admin.

### Cong viec

- Them tab hoac route `System Health` trong Admin Settings.
- Hien thi cac service theo dang danh sach/card gon:
  - System
  - Postgres
  - Qdrant
  - Redis
  - Workers
- Doi gia tri boolean `true/false` thanh ngon ngu de hieu:
  - `true` -> `Connected` hoac `Healthy`
  - `false` -> `Disconnected` hoac `Error`
- Them thoi gian cap nhat gan nhat.
- Them nut refresh neu API ho tro.

### Ket qua mong doi

Admin co mot noi ro rang de kiem tra tinh trang he thong.

## Phase 3 - Them indicator nho trong Admin Header

### Muc tieu

Cho admin biet nhanh he thong dang OK hay co van de ma khong can vao trang chi tiet.

### Cong viec

- Them badge nho trong header admin.
- Trang thai:
  - `OK`
  - `Warning`
  - `Error`
- Bam badge mo popover tom tat.
- Popover co nut `Open System Health`.

### Ket qua mong doi

Admin van nhan biet duoc su co nhanh, nhung UI khong bi day thong tin ky thuat ra ngoai.

## Phase 4 - Phan quyen hien thi

### Muc tieu

Chi nguoi co quyen phu hop moi thay thong tin ky thuat he thong.

### Cong viec

- Super admin: xem day du System Health.
- Admin: xem tong quan va trang thai dich vu neu duoc phep.
- Operator/user van hanh camera: khong thay dong health/status.
- Neu can, chi hien loi nghiem trong lien quan truc tiep den van hanh camera, vi du "He thong xu ly canh bao dang gian doan".

### Ket qua mong doi

Thong tin ky thuat khong lam roi nguoi dung khong can no.

## Phase 5 - Kiem thu UX

### Tinh huong can kiem tra

- Dashboard khi he thong OK.
- Dashboard khi mot service loi.
- Admin Settings > System Health khi tat ca service OK.
- Admin Settings > System Health khi Postgres/Redis/Qdrant loi.
- Workers 0/3, 1/3, 3/3.
- User khong co quyen admin truy cap Dashboard.

### Tieu chi dat

- Dashboard khong con dong status ky thuat.
- Admin van xem duoc health/status day du.
- Trang thai hien thi bang ngon ngu de hieu, khong phai `true/false`.
- Loi quan trong khong bi che giau voi admin.
- UI gon, khong gay vuong man hinh camera.

## Ket luan

Nen dua dong health/status vao `Admin Settings > System Health`, dong thoi them mot indicator nho trong Admin Header cho nguoi co quyen. Dashboard camera khong nen hien thong tin nay vi no khong phuc vu truc tiep cho viec quan sat camera.
