# Ke hoach tach canh bao khoi Dashboard

## Muc tieu

Dashboard chi tap trung hien thi cac luong camera. Canh bao moi se duoc hien thi bang lop thong bao noi, co co che gom nhom de tranh tran man hinh va co trung tam thong bao de nguoi dung khong bi miss.

## Nguyen tac giao dien

- Dashboard la khu vuc chinh cho camera grid, khong dat block "canh bao moi nhat" co dinh tren trang.
- Popup chi dung de bao hieu nhanh, khong phai noi luu tru day du canh bao.
- Moi canh bao phai co duong lui: neu nguoi dung bo lo popup thi van xem lai duoc trong notification center.
- Uu tien canh bao theo muc do nghiem trong, thoi gian, camera va loai su kien.
- Khong de popup xep day man hinh.

## Phase 1 - Don dep Dashboard va dinh nghia luong canh bao

### Muc tieu

Chuyen Dashboard ve dung vai tro la man hinh giam sat camera, dong thoi xac dinh du lieu toi thieu can cho mot canh bao.

### Cong viec

- Go bo hoac an block "canh bao moi nhat" dang hien truc tiep tren trang Dashboard.
- Giu lai layout camera grid lam noi dung chinh.
- Chuan hoa model canh bao gom:
  - `id`
  - `type`
  - `cameraName`
  - `location`
  - `timestamp`
  - `severity`
  - `snapshotUrl`
  - `status`
- Xac dinh cac muc do canh bao: `high`, `medium`, `low`.
- Xac dinh hanh dong chinh: `Xem ngay`, `Da xu ly`, `Bo qua`.

### Ket qua mong doi

Dashboard trong gon hon, khong bi canh bao chiem dien tich, nhung he thong van co day du du lieu de hien thong bao noi.

## Phase 2 - Popup canh bao noi

### Muc tieu

Khi co canh bao moi, hien popup ngan gon de nguoi dung nhan ra ngay ma khong roi khoi man hinh camera.

### Giao dien de xuat

Vi tri: goc phai tren hoac phai duoi man hinh.

Noi dung popup:

```text
Canh bao moi
Phat hien nguoi la tai Camera Cong chinh
14:32 - Muc do cao

[Xem ngay]
```

### Quy tac hien thi

- Chi hien toi da 2 popup cung luc.
- Canh bao muc `high` khong tu dong bien mat qua nhanh.
- Canh bao muc `medium` va `low` co the tu dong an sau 6-10 giay.
- Popup co nut dong thu cong.
- Bam `Xem ngay` se mo modal chi tiet canh bao.

### Ket qua mong doi

Nguoi dung thay canh bao moi kip thoi, nhung Dashboard khong bi chen noi dung.

## Phase 3 - Gom nhom khi co nhieu canh bao

### Muc tieu

Tranh viec nhieu popup xuat hien cung luc gay tran man hinh.

### Quy tac gom nhom

- Neu dang co 2 popup hien thi, canh bao moi tiep theo se khong tao them popup rieng.
- Cac canh bao duoc gom thanh mot popup tong hop:

```text
Co 7 canh bao moi
Camera Cong chinh, Kho A, Hanh lang tang 2

[Xem tat ca]
```

- Neu co canh bao `high`, uu tien hien rieng canh bao do.
- Cac canh bao trung camera, trung loai, gan nhau ve thoi gian nen gom lai.
- Popup tong hop cap nhat so luong theo thoi gian thuc.

### Ket qua mong doi

Du co nhieu canh bao cung luc, giao dien van gon va nguoi dung van nam duoc tinh hinh.

## Phase 4 - Notification Center

### Muc tieu

Tao noi luu lai toan bo canh bao de nguoi dung xem lai khi miss popup.

### Giao dien de xuat

- Them icon chuong tren Dashboard.
- Hien badge so luong canh bao chua doc, vi du: `12`.
- Bam icon chuong mo panel danh sach canh bao gan day.

### Danh sach canh bao nen co

- Loai canh bao.
- Camera/khu vuc.
- Thoi gian.
- Muc do nghiem trong.
- Trang thai: chua doc, da xem, da xu ly.
- Nut xem chi tiet.

### Ket qua mong doi

Popup khong con la kenh duy nhat. Nguoi dung co the xem lai lich su canh bao bat cu luc nao.

## Phase 5 - Modal chi tiet canh bao

### Muc tieu

Cho phep nguoi dung xem nhanh thong tin quan trong cua canh bao ma khong lam mat boi canh Dashboard.

### Noi dung modal

- Anh snapshot hoac frame tai thoi diem phat hien.
- Ten camera va vi tri.
- Thoi gian phat hien.
- Loai phat hien.
- Muc do nghiem trong.
- Trang thai xu ly.
- Nut `Da xu ly`, `Bo qua`, `Mo camera`.

### Ket qua mong doi

Nguoi dung co the danh gia va xu ly canh bao nhanh ngay tren Dashboard.

## Phase 6 - Chong miss thong bao

### Muc tieu

Dam bao canh bao quan trong khong bi bo sot, dac biet khi nguoi dung dang tap trung vao camera.

### De xuat

- Canh bao `high` can yeu cau nguoi dung dong hoac danh dau da xem.
- Badge chuong giu so luong canh bao chua doc.
- Co trang thai da doc/chua doc ro rang.
- Co am thanh nhe cho canh bao quan trong neu phu hop voi moi truong su dung.
- Co mau sac rieng cho muc do nghiem trong:
  - High: do/cam dam, can chu y ngay.
  - Medium: vang/cam nhe.
  - Low: xam/xanh nhe.

### Ket qua mong doi

Nguoi dung khong bi ngop vi popup, nhung canh bao quan trong van duoc nhan dien ro.

## Phase 7 - Kiem thu va tinh chinh UX

### Tinh huong can test

- Mot canh bao moi xuat hien.
- Nhieu canh bao xuat hien gan nhu cung luc.
- Co ca `high`, `medium`, `low` cung luc.
- Nguoi dung bo lo popup va mo notification center.
- Nguoi dung bam `Xem ngay`.
- Nguoi dung danh dau `Da xu ly`.
- Man hinh desktop va mobile/tablet.

### Tieu chi dat

- Dashboard van uu tien camera grid.
- Popup khong bao gio tran man hinh.
- Canh bao moi de nhan ra.
- Canh bao bi miss van xem lai duoc.
- Nguoi dung co du luong thao tac de xu ly canh bao.

## Thu tu uu tien de trien khai

1. Tach block canh bao khoi Dashboard.
2. Lam popup canh bao toi da 2 item.
3. Them co che gom `+N canh bao moi`.
4. Them icon chuong va notification center.
5. Them modal chi tiet canh bao.
6. Bo sung trang thai doc/xu ly va tinh chinh UX.
