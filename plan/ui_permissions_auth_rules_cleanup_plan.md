# UI, Phan Quyen, Auth, Thong Bao va Thiet Lap Van Hanh Cleanup Plan

Muc tieu: dong bo UI theo theme hien tai, giam khoang trong thua, thuan tieng Viet, don quyen thanh de hieu hon, bo dang ky cong khai, an thong tin ky thuat voi user khong can xem, sap xep lai sidebar, va lam trang thiet lap van hanh gon/de dung hon.

## Nguyen tac chung

- Giu dung ten he thong hien tai: `NTC Anonymous Detection & Recognition`.
- Giao dien nguoi dung phai uu tien tieng Viet.
- Khong hien raw key tieng Anh nhu `unknown_detection`, `full frame`, `users`, `system monitor`, ...
- Khong dua thong tin ky thuat cho user cap xem/lanh dao.
- UI phai gon hon nhung khong bi chat.
- Moi thay doi lien quan auth/phan quyen phai tranh gay loi dang nhap va tao tai khoan.
- Phan mo ta o trang He thong tam thoi chua lam chi tiet; doi user mo ta sau.

## Phase 1: Don banner/topbar va bo thong tin tai khoan lap lai

### Viec can lam

1. Bo phan thong tin tai khoan nam duoi banner/topbar tung trang.
   - Vi du dang hien kieu: `Tai khoan dang dang nhap: admin ...`
   - Khong lap lai thong tin account o moi banner.
   - Neu can hien tai khoan thi chi de tai khu vuc sidebar/account menu.

2. Giam cac dong mo ta dai trong banner.
   - Chi de tieu de trang.
   - Mo ta ngan chi giu o nhung trang that su can.

3. Rieng trang He thong:
   - Tam thoi bo mo ta dai.
   - De placeholder/toi gian.
   - Doi user mo ta sau roi moi viet noi dung chinh thuc.

### File lien quan

- `frontend/src/components/AdminShell.tsx`
- `frontend/src/app/globals.css`

### Ket qua mong muon

- Banner gon hon.
- Khong con thong tin tai khoan lap lai duoi tung banner.
- Trang He thong khong con mo ta dai chua chot.

## Phase 2: Doi thong bao/canh bao tu dang cot ben thanh dang ngang nguyen trang

### Van de hien tai

- Phan thong bao dang nam mot ben, giong panel/doc/cot.
- Khong tan dung chieu ngang man hinh.
- Khi co nhieu thong bao/canh bao, nhin bi hep va kho scan.

### Huong sua

1. Chuyen khu vuc thong bao/canh bao sang layout ngang theo trang.
   - Uu tien dang full-width section.
   - Moi thong bao la card ngang co thong tin chinh ro rang.
   - Neu nhieu thong bao thi dung list/table-like layout de scan nhanh.

2. Bo cuc de xuat cho moi dong thong bao:
   - Ben trai: muc do canh bao + loai canh bao.
   - Giua: noi dung chinh + camera/khu vuc.
   - Ben phai: thoi gian + nut xem chi tiet/xu ly.

3. Voi popup realtime:
   - Neu van giu popup thi phai gon, khong che noi dung chinh.
   - Neu chuyen sang trang canh bao thi nut/link phai dua user ve danh sach canh bao ngang.

4. Viet hoa toan bo label trong thong bao.
   - `Alert`, `Warning`, `Unknown`, `Critical`, ... phai map sang tieng Viet.

### File lien quan

- `frontend/src/components/AlertNotifications.tsx`
- `frontend/src/components/AlertsPanel.tsx`
- `frontend/src/lib/alertText.ts`
- `frontend/src/app/globals.css`

### Ket qua mong muon

- Phan thong bao/canh bao rong theo chieu ngang, de doc hon.
- Khong con cam giac bi ep thanh mot cot ben.
- De scan nhieu canh bao cung luc.

## Phase 3: An thong tin ky thuat canh bao theo quyen

### Viec can lam

1. An hoan toan dropdown `Thong tin ky thuat` voi viewer/user cap xem.
   - Khong render phan nay.
   - Khong chi disable.

2. Chi admin/sub admin moi thay thong tin ky thuat.
   - Dung role hien co hoac helper permission.
   - Neu can them helper: `canViewAlertTechnicalDetails(user)`.

3. Ap dung cho ca hai noi:
   - Modal chi tiet trong trang canh bao.
   - Modal chi tiet tu notification/realtime popup.

### File lien quan

- `frontend/src/components/AlertsPanel.tsx`
- `frontend/src/components/AlertNotifications.tsx`
- `frontend/src/lib/permissions.ts`
- `frontend/src/lib/types.ts`

### Ket qua mong muon

- Sep/viewer khong thay thong tin ky thuat.
- Admin/sub admin van thay de van hanh/debug.

## Phase 4: Viet hoa toan bo UI va loai canh bao

### Viec can lam

1. Ra soat toan bo UI de bo tieng Anh dan xen.
   - `Dashboard`
   - `Employees`
   - `Users`
   - `System Monitor`
   - `Username`
   - `Password`
   - `Full frame`
   - `Unknown`
   - `Critical`
   - Cac raw type/status/key tu API.

2. Chuan hoa nhan tieng Viet.
   - `Dashboard` -> `Tong quan` hoac `Trung tam camera`
   - `Employees` -> `Nhan vien`
   - `Users` -> `Tai khoan`
   - `System Monitor` -> `He thong`
   - `Username` -> `Ten dang nhap`
   - `Password` -> `Mat khau`
   - `Full frame` -> `Anh toan canh`
   - `Unknown` -> `Nguoi la` hoac `Khong xac dinh` tuy ngu canh

3. Dac biet phan `Loai canh bao`.
   - Khong hien raw value tieng Anh.
   - Them/sua helper trong `alertText.ts`.
   - Tat ca loai canh bao phai co label tieng Viet.

4. Neu API tra gia tri moi chua map:
   - Hien fallback tieng Viet an toan: `Canh bao khac`
   - Khong hien truc tiep raw key.

### File lien quan

- `frontend/src/lib/alertText.ts`
- `frontend/src/lib/ruleText.ts`
- `frontend/src/components/AdminShell.tsx`
- `frontend/src/components/AlertsPanel.tsx`
- `frontend/src/components/AlertNotifications.tsx`
- `frontend/src/components/UsersPanel.tsx`
- `frontend/src/components/EmployeesList.tsx`
- `frontend/src/components/SystemAnalyticsPanel.tsx`
- `frontend/src/components/LoginForm.tsx`

### Ket qua mong muon

- UI nguoi dung gan nhu 100% tieng Viet.
- Khong con tieng Anh dan xen o label, menu, loai canh bao, role, status.

## Phase 5: Don quyen thanh admin/sub admin/viewer

### Viec can lam

1. Rut gon nhom quyen thanh 3 nhom de hieu:
   - `Admin`
   - `Sub admin`
   - `Viewer`

2. Mapping de xuat voi role number hien tai:
   - Role `9` -> `Admin`
   - Role `5` -> `Sub admin`
   - Role `0` hoac role xem -> `Viewer`

3. Xu ly role `1` hien tai neu dang ton tai.
   - Phuong an A: map role `1` ve `Viewer` neu chi xem/it quyen.
   - Phuong an B: map role `1` ve `Sub admin` neu dang co quyen truc ca/xu ly canh bao.
   - Can kiem tra permission thuc te truoc khi chot.

4. Cap nhat mo ta quyen:
   - `Admin`: Toan quyen he thong.
   - `Sub admin`: Quan ly van hanh va xu ly canh bao.
   - `Viewer`: Chi xem dashboard/canh bao duoc phep, khong xem thong tin ky thuat.

5. Cap nhat UI phan quyen.
   - Modal chon role chi hien 3 lua chon.
   - Badge role tren sidebar/bang tai khoan dung 3 ten moi.

### File lien quan

- `frontend/src/components/UsersPanel.tsx`
- `frontend/src/components/AdminShell.tsx`
- `frontend/src/lib/permissions.ts`
- `backend/auth/security.py` neu role backend co rang buoc
- `backend/users/router.py` neu validate role

### Ket qua mong muon

- Quyen de hieu hon: admin/sub admin/viewer.
- Khong con nhieu cap quyen gay roi.

## Phase 6: Bo dang ky cong khai va dam bao auth an toan

### Viec can lam

1. Bo link `Dang ky` khoi man dang nhap.
   - Tai khoan se duoc cap boi admin/sub admin.

2. Xu ly route `/register`.
   - Uu tien redirect ve `/login`.
   - Hoac hien trang thong bao: `Tai khoan duoc cap boi quan tri vien.`
   - Khong cho tu dang ky cong khai.

3. Kiem tra backend register endpoint.
   - Neu `/register` dang public thi khoa lai.
   - Chi admin/sub admin duoc tao tai khoan qua trang `Tai khoan`.

4. Bao mat de khong loi.
   - Truy cap `/register` truc tiep khong crash.
   - Login khong bi anh huong.
   - Token/session hien tai van hoat dong.
   - Khi token het han van redirect ve login.

5. Neu backend van can endpoint tao user:
   - Chuyen sang endpoint admin-only.
   - Yeu cau token va permission tao tai khoan.

### File lien quan

- `frontend/src/components/LoginForm.tsx`
- `frontend/src/app/register/page.tsx`
- `frontend/src/lib/api.ts`
- `backend/auth/router.py`
- `backend/users/router.py`
- `backend/auth/security.py`

### Ket qua mong muonfailure to get a peer from the ring-balancer

- Khong con dang ky cong khai.
- Tai khoan chi duoc cap noi bo.
- Khong lam hong login/session hien co.

## Phase 7: Sap xep lai sidebar va lam sidebar gon ro hon

### Van de hien tai

- Sidebar rong qua.
- Khung sidebar chua ro.
- Menu sap xep dang lung tung.
- Khoang trong trong sidebar va trang thiet lap con nhieu.

### Viec can lam

1. Thu hep sidebar.
   - Giam width tu khoang `320px` xuong `260px - 280px`.
   - Dam bao text menu van khong vo xau.

2. Lam khung sidebar ro hon.
   - Them border nhe.
   - Them box-shadow ben phai.
   - Background dong bo theme hien tai.

3. Giam khoang trong.
   - Nav item gon hon.
   - Description menu neu dai thi rut ngan hoac an bot.
   - Account block gon lai.

4. Sap xep menu lai theo thu tu de dung:
   - `Tong quan`
   - `Camera`
   - `Canh bao`
   - `Thiet lap van hanh`
   - `Nhan vien`
   - `Tai khoan`
   - `He thong`

5. Dong bo voi phan quyen.
   - Viewer khong thay menu khong du quyen.
   - Sub admin thay cac menu van hanh.
   - Admin thay tat ca.

### File lien quan

- `frontend/src/components/AdminShell.tsx`
- `frontend/src/app/globals.css`

### Ket qua mong muon

- Sidebar hep hon, co border/shadow ro.
- Menu sap xep logic hon.
- Tong the bot trong va bot bi dai.

## Phase 8: Lam lai trang Thiet lap van hanh

### Van de hien tai

- Trang co qua nhieu cho trong.
- Mot so phan lai bi dan rong, khong can doi.
- `Quy tac phat hien nguoi la` chua duoc dua len vung trong phia tren.
- Phan ROI chua de hieu voi user.

### Huong sua bo cuc

1. Dua `Quy tac phat hien nguoi la` len phan tren.
   - Bien no thanh card gon.
   - Dat vao vung dang trong phia tren.
   - Hien nhanh cac thong tin quan trong:
     - Trang thai bat/tat.
     - Nguong thoi gian.
     - Camera/khu vuc ap dung.
     - Muc do canh bao.

2. Bop lai khoang trong cua trang.
   - Giam padding/gap qua lon.
   - Dung grid 2 cot desktop.
   - Mobile ve 1 cot.
   - Khong de card rong ma it noi dung.

3. Khong lam qua chat.
   - Moi card van co khoang tho.
   - Button/input khong dinh nhau.
   - Label ngan, de doc.

4. Phan ROI doi ten cho de hieu.
   - Khong hien `ROI` don doc neu user khong hieu.
   - Goi y label:
     - `Vung canh bao`
     - `Khu vuc giam sat`
     - `Vung theo doi`
   - Goi y chot: dung `Vung canh bao` neu ROI dung de khoanh vung canh bao.
   - Co the ghi nho nho cho admin: `ROI` chi nam trong tooltip/technical text neu can.

5. Toggle ROI/vung canh bao.
   - Doi thanh tieng Viet:
     - `Bat vung canh bao`
     - `Tat vung canh bao`
     - `Dang bat`
     - `Dang tat`
   - Nut sua vung:
     - `Chinh sua vung`
     - `Luu vung`
     - `Huy`

### File lien quan

- `frontend/src/components/RulesPanel.tsx`
- `frontend/src/components/LiveMonitor.tsx` neu ROI editor nam o live monitor
- `frontend/src/app/globals.css`
- `frontend/src/lib/ruleText.ts`
- `frontend/src/lib/types.ts`

### Ket qua mong muon

- Trang Thiet lap van hanh day du hon nhung khong roi.
- Quy tac phat hien nguoi la nam o tren va gon.
- Phan ROI/vung canh bao de hieu voi user.
- It khoang trong thua.

## Phase 9: Xu ly phan He thong sau khi co mo ta moi

### Trang thai

- Chua lam chi tiet ngay.
- User se mo ta sau roi moi thuc hien.

### Viec tam thoi

1. Bo mo ta dai hien tai.
2. Giu layout gon.
3. Chi de cac thong tin can thiet da co.

### File lien quan

- `frontend/src/components/SystemAnalyticsPanel.tsx`
- `frontend/src/components/AdminShell.tsx`
- `frontend/src/app/system/page.tsx`

### Ket qua mong muon

- Trang He thong khong bi day boi mo ta chua chot.
- San sang cap nhat khi co noi dung moi.

## Phase 10: Kiem thu cuoi

### Lenh can chay

```bash
cd frontend
npm run typecheck
```

Neu sua backend auth/register:

```bash
python -m compileall backend
```

### Route can kiem tra

- `/login`
- `/register`
- `/`
- `/alerts`
- `/rules`
- `/users`
- `/system`

### Checklist

1. Auth:
   - Login van hoat dong.
   - Khong con link dang ky.
   - Truy cap `/register` truc tiep khong tao duoc tai khoan.

2. Phan quyen:
   - Viewer khong thay thong tin ky thuat canh bao.
   - Sub admin/admin thay neu du quyen.
   - Role hien thi chi con admin/sub admin/viewer.

3. Viet hoa:
   - Loai canh bao hien tieng Viet.
   - Menu/sidebar tieng Viet.
   - Form/login/tai khoan tieng Viet.
   - Khong hien raw key tieng Anh.

4. Sidebar:
   - Hep hon.
   - Co border/shadow.
   - Menu sap xep dung thu tu moi.
   - Khong bi trong qua nhieu.

5. Thiet lap van hanh:
   - Quy tac phat hien nguoi la da dua len tren.
   - Trang khong qua trong, khong qua chat.
   - ROI da doi thanh `Vung canh bao` hoac nhan tieng Viet de hieu.

6. Thong bao/canh bao:
   - Layout thong bao/canh bao dung chieu ngang trang.
   - De scan va khong bi ep thanh cot ben.

## Thu tu uu tien de lam ngay mai

1. Phase 6: Bo dang ky cong khai va dam bao auth an toan.
2. Phase 3: An thong tin ky thuat canh bao theo quyen.
3. Phase 4: Viet hoa UI va loai canh bao.
4. Phase 5: Don quyen thanh admin/sub admin/viewer.
5. Phase 7: Sap xep va thu gon sidebar.
6. Phase 2: Doi thong bao/canh bao sang layout ngang.
7. Phase 8: Lam lai trang Thiet lap van hanh va vung canh bao.
8. Phase 1: Don banner/topbar trong qua trinh lam cac man.
9. Phase 9: Tam thoi bo mo ta dai o He thong, doi user mo ta sau.
10. Phase 10: Kiem thu cuoi.

## Ghi chu thuc hien

- Moi phase nen commit rieng neu dung git.
- Sau moi phase frontend nen chay `npm run typecheck`.
- Khi sua auth/register can test ca frontend va backend.
- Khi doi role can kiem tra permission that su de khong khoa nham admin.
- Khi Viet hoa raw key, nen lam qua helper mapping thay vi sua truc tiep tung component.
