# HÆ°á»›ng Ä‘i triá»ƒn khai há»‡ thá»‘ng phÃ¡t hiá»‡n ngÆ°á»i láº¡ cháº¡y InsightFace local vÃ  Qdrant

## 1. Má»¥c tiÃªu bÃ i toÃ¡n

Há»‡ thá»‘ng sáº½ cháº¡y **InsightFace trá»±c tiáº¿p trÃªn mÃ¡y cá»§a mÃ¬nh** Ä‘á»ƒ xá»­ lÃ½ camera/video local. KhÃ´ng cáº§n train láº¡i model, chá»‰ dÃ¹ng cÃ¡c model cÃ³ sáºµn cá»§a InsightFace cho hai pháº§n chÃ­nh:

- **Face detection**: phÃ¡t hiá»‡n khuÃ´n máº·t trong frame.
- **Face recognition**: trÃ­ch xuáº¥t embedding khuÃ´n máº·t Ä‘á»ƒ so khá»›p.
- Truy váº¥n database Qdrant Ä‘á»ƒ so khá»›p ngÆ°á»i Ä‘Ã£ Ä‘Äƒng kÃ½.
- Hiá»ƒn thá»‹ ngÆ°á»i Ä‘Ã£ biáº¿t báº±ng **khung xanh + tÃªn trong database**.
- Hiá»ƒn thá»‹ ngÆ°á»i láº¡ báº±ng **khung Ä‘á» + nhÃ£n Unknown**.
- XÃ¢y dá»±ng cÆ¡ cháº¿ cáº£nh bÃ¡o khi ngÆ°á»i láº¡ cÃ³ hÃ nh vi Ä‘Ã¡ng ngá», vÃ­ dá»¥:
  - Xuáº¥t hiá»‡n ngoÃ i giá» lÃ m viá»‡c.
  - Láº£ng váº£ng á»Ÿ khu vá»±c cá»•ng.
  - Äi vÃ o khu vá»±c háº¡n cháº¿.
  - Xuáº¥t hiá»‡n nhiá»u láº§n trong má»™t khoáº£ng thá»i gian ngáº¯n.
- Khi cÃ³ cáº£nh bÃ¡o, há»‡ thá»‘ng sáº½:
  - Chá»¥p láº¡i áº£nh ngÆ°á»i láº¡.
  - LÆ°u log sá»± kiá»‡n.
  - Gá»­i cáº£nh bÃ¡o lÃªn giao diá»‡n hoáº·c há»‡ thá»‘ng thÃ´ng bÃ¡o.

---

## 2. Äá»‹nh hÆ°á»›ng tá»•ng thá»ƒ

HÆ°á»›ng lÃ m chÃ­nh:

> KhÃ´ng train model má»›i, cháº¡y model InsightFace local trÃªn mÃ¡y cá»§a mÃ¬nh, dÃ¹ng detection Ä‘á»ƒ láº¥y bbox khuÃ´n máº·t vÃ  recognition Ä‘á»ƒ láº¥y embedding, sau Ä‘Ã³ query Qdrant Ä‘á»ƒ phÃ¢n loáº¡i Known / Unknown rá»“i Ä‘Æ°a vÃ o Rule Engine phÃ¡t hiá»‡n ngÆ°á»i láº¡ Ä‘Ã¡ng nghi.

Model nguá»“n tham kháº£o:

- Detection: `https://github.com/deepinsight/insightface/tree/master/detection`
- Recognition: `https://github.com/deepinsight/insightface/tree/master/recognition`

Luá»“ng tá»•ng thá»ƒ:

```text
Camera / Video Stream
        â†“
InsightFace local detection
        â†“
Crop / align face
        â†“
InsightFace local recognition
        â†“
Nháº­n embedding khuÃ´n máº·t
        â†“
Query Qdrant database
        â†“
Láº¥y top-1 hoáº·c top-k káº¿t quáº£ gáº§n nháº¥t
        â†“
So sÃ¡nh score vá»›i threshold
        â†“
Known / Unknown / Unverified
        â†“
Hiá»ƒn thá»‹ bounding box
        â†“
Rule Engine kiá»ƒm tra Ä‘iá»u kiá»‡n cáº£nh bÃ¡o
        â†“
LÆ°u snapshot + log + warning
```

---

## 3. Kiáº¿n trÃºc há»‡ thá»‘ng Ä‘á» xuáº¥t

```text
â”Œâ”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”
â”‚ Camera / RTSP / Video â”‚
â””â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”¬â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”˜
            â†“
â”Œâ”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”
â”‚ Frame Capture         â”‚
â”‚ OpenCV                â”‚
â””â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”¬â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”˜
            â†“
â”Œâ”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”
â”‚ InsightFace Detection â”‚
â”‚ cháº¡y local            â”‚
â””â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”¬â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”˜
            â†“
â”Œâ”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”
â”‚ InsightFace Recognitionâ”‚
â”‚ cháº¡y local, extract embâ”‚
â””â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”¬â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”˜
            â†“
â”Œâ”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”
â”‚ Qdrant Vector Search  â”‚
â”‚ Search employee DB    â”‚
â””â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”¬â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”˜
            â†“
â”Œâ”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”
â”‚ Recognition Decision  â”‚
â”‚ Known / Unknown       â”‚
â””â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”¬â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”˜
            â†“
â”Œâ”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”
â”‚ Tracking + Voting     â”‚
â”‚ Reduce false alert    â”‚
â””â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”¬â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”˜
            â†“
â”Œâ”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”
â”‚ Rule Engine           â”‚
â”‚ Time + Zone + Behaviorâ”‚
â””â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”¬â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”˜
            â†“
â”Œâ”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”
â”‚ Alert + Snapshot + Logâ”‚
â””â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”˜
```

---

## 4. CÃ¡c tráº¡ng thÃ¡i cáº§n phÃ¢n biá»‡t

KhÃ´ng nÃªn chá»‰ chia thÃ nh 2 tráº¡ng thÃ¡i Known / Unknown. NÃªn chia thÃ nh 3 tráº¡ng thÃ¡i:

| Tráº¡ng thÃ¡i | Ã nghÄ©a | Hiá»ƒn thá»‹ |
|---|---|---|
| `Known` | NgÆ°á»i Ä‘Ã£ cÃ³ trong database, score vÆ°á»£t threshold | Khung xanh + tÃªn |
| `Unknown` | CÃ³ máº·t rÃµ nhÆ°ng khÃ´ng khá»›p ai trong database | Khung Ä‘á» + Unknown |
| `Unverified` | KhÃ´ng Ä‘á»§ Ä‘iá»u kiá»‡n nháº­n diá»‡n: máº·t má», nhá», quay lÆ°ng, che máº·t | Khung vÃ ng/xÃ¡m + Unverified |

LÃ½ do cáº§n cÃ³ `Unverified`:

- Náº¿u khÃ´ng tháº¥y rÃµ máº·t thÃ¬ khÃ´ng nÃªn káº¿t luáº­n cháº¯c cháº¯n lÃ  ngÆ°á»i láº¡.
- Tráº¡ng thÃ¡i nÃ y giÃºp giáº£m cáº£nh bÃ¡o sai.
- CÃ³ thá»ƒ dÃ¹ng thÃªm rule riÃªng: náº¿u `Unverified` vÃ o khu vá»±c cáº¥m hoáº·c ngoÃ i giá» thÃ¬ cáº£nh bÃ¡o má»©c trung bÃ¬nh.

---

## 5. Logic nháº­n diá»‡n Known / Unknown

### 5.1. Input

- Frame tá»« camera/video.
- Bbox khuÃ´n máº·t tá»« InsightFace detection cháº¡y local.
- Face crop hoáº·c aligned face.
- Embedding tá»« InsightFace recognition cháº¡y local.
- Database Qdrant chá»©a embedding nhÃ¢n viÃªn.

### 5.2. Output

- `status`: Known / Unknown / Unverified.
- `name`: tÃªn nhÃ¢n viÃªn hoáº·c Unknown.
- `score`: Ä‘iá»ƒm tÆ°Æ¡ng Ä‘á»“ng.
- `employee_id`: mÃ£ nhÃ¢n viÃªn náº¿u cÃ³.
- `bbox`: tá»a Ä‘á»™ khuÃ´n máº·t.
- `camera_id`: camera phÃ¡t hiá»‡n.
- `timestamp`: thá»i gian phÃ¡t hiá»‡n.

### 5.3. Logic cÆ¡ báº£n

```python
if face_quality_is_low:
    status = "unverified"
elif best_score >= FACE_THRESHOLD:
    status = "known"
    label = employee_name
    box_color = "green"
else:
    status = "unknown"
    label = "Unknown"
    box_color = "red"
```

### 5.4. Threshold ban Ä‘áº§u

CÃ³ thá»ƒ thá»­ ban Ä‘áº§u:

```python
FACE_THRESHOLD = 0.55  # hoáº·c 0.60
```

Tuy nhiÃªn threshold khÃ´ng nÃªn chá»n cá»‘ Ä‘á»‹nh theo cáº£m tÃ­nh. Cáº§n test trÃªn dá»¯ liá»‡u camera tháº­t cá»§a cÃ´ng ty.

Gá»£i Ã½ cÃ¡ch chá»n threshold:

| TrÆ°á»ng há»£p | Ã nghÄ©a |
|---|---|
| Threshold tháº¥p | Dá»… nháº­n nháº§m ngÆ°á»i láº¡ thÃ nh nhÃ¢n viÃªn |
| Threshold cao | Dá»… nháº­n nháº§m nhÃ¢n viÃªn thÃ nh ngÆ°á»i láº¡ |
| Threshold phÃ¹ há»£p | CÃ¢n báº±ng giá»¯a false accept vÃ  false reject |

NÃªn thu dá»¯ liá»‡u test gá»“m:

- áº¢nh nhÃ¢n viÃªn tá»« camera tháº­t.
- áº¢nh ngÆ°á»i ngoÃ i khÃ´ng cÃ³ trong database.
- áº¢nh nhÃ¢n viÃªn á»Ÿ nhiá»u gÃ³c khÃ¡c nhau.
- áº¢nh trong Ä‘iá»u kiá»‡n thiáº¿u sÃ¡ng, ngÆ°á»£c sÃ¡ng, Ä‘i nhanh.

---

## 6. Vai trÃ² cá»§a Qdrant

Qdrant Ä‘Æ°á»£c dÃ¹ng lÃ m vector database Ä‘á»ƒ lÆ°u vÃ  truy váº¥n embedding khuÃ´n máº·t.

### 6.1. Dá»¯ liá»‡u trong Qdrant cáº§n cÃ³

Má»—i vector nÃªn cÃ³ payload dáº¡ng:

```json
{
  "employee_id": "EMP001",
  "name": "Nguyen Van A",
  "department": "IT",
  "role": "Staff",
  "image_path": "employees/EMP001.jpg"
}
```

### 6.2. Äiá»u kiá»‡n báº¯t buá»™c

Cáº§n Ä‘áº£m báº£o:

- Embedding trong Qdrant vÃ  embedding má»›i pháº£i Ä‘Æ°á»£c táº¡o tá»« cÃ¹ng model recognition cá»§a InsightFace.
- Náº¿u Ä‘á»•i model recognition local, pháº£i táº¡o láº¡i embedding trong Qdrant báº±ng Ä‘Ãºng model Ä‘Ã³.
- CÃ¹ng sá»‘ chiá»u vector, vÃ­ dá»¥ 512 chiá»u.
- CÃ¹ng cÃ¡ch normalize vector.
- CÃ¹ng metric search, vÃ­ dá»¥ cosine similarity.
- Payload cÃ³ Ä‘á»§ thÃ´ng tin Ä‘á»ƒ hiá»ƒn thá»‹ tÃªn ngÆ°á»i.

### 6.3. Query Qdrant

Luá»“ng query:

```text
Embedding má»›i
   â†“
Qdrant search top-1 hoáº·c top-5
   â†“
Láº¥y káº¿t quáº£ cÃ³ score cao nháº¥t
   â†“
So sÃ¡nh vá»›i threshold
```

Ban Ä‘áº§u cÃ³ thá»ƒ dÃ¹ng `top_k = 1`. Sau Ä‘Ã³ náº¿u muá»‘n debug tá»‘t hÆ¡n thÃ¬ dÃ¹ng `top_k = 5` Ä‘á»ƒ biáº¿t Unknown Ä‘ang gáº§n giá»‘ng nhá»¯ng ai.

---

## 7. KhÃ´ng cáº£nh bÃ¡o ngay khi tháº¥y Unknown

Má»™t lá»—i ráº¥t thÆ°á»ng gáº·p lÃ  vá»«a phÃ¡t hiá»‡n Unknown Ä‘Ã£ cáº£nh bÃ¡o ngay. Äiá»u nÃ y dá»… gÃ¢y spam vÃ  bÃ¡o sai.

NÃªn chia thÃ nh 2 táº§ng:

```text
Táº§ng 1: Unknown Detection
Táº§ng 2: Suspicious Unknown Warning
```

CÃ³ nghÄ©a lÃ :

- `Unknown` thÃ´ng thÆ°á»ng: chá»‰ váº½ khung Ä‘á».
- `Unknown + Ä‘iá»u kiá»‡n Ä‘Ã¡ng ngá»`: má»›i cáº£nh bÃ¡o.

VÃ­ dá»¥:

```text
Unknown xuáº¥t hiá»‡n trong giá» lÃ m viá»‡c á»Ÿ khu vá»±c bÃ¬nh thÆ°á»ng
â†’ Chá»‰ hiá»ƒn thá»‹ khung Ä‘á»

Unknown xuáº¥t hiá»‡n ngoÃ i giá» lÃ m viá»‡c
â†’ Warning

Unknown Ä‘á»©ng á»Ÿ cá»•ng quÃ¡ lÃ¢u
â†’ Warning

Unknown Ä‘i vÃ o khu vá»±c háº¡n cháº¿
â†’ Warning
```

---

## 8. Rule Engine cáº£nh bÃ¡o

Rule Engine lÃ  module quyáº¿t Ä‘á»‹nh khi nÃ o cáº§n cáº£nh bÃ¡o.

### 8.1. Rule 1: NgÆ°á»i láº¡ xuáº¥t hiá»‡n ngoÃ i giá» lÃ m viá»‡c

VÃ­ dá»¥ giá» lÃ m viá»‡c:

```text
08:00 - 17:30
```

Logic:

```python
if status == "unknown" and not is_working_hour(current_time):
    warning_type = "unknown_outside_working_hours"
    level = "high"
```

ThÃ´ng bÃ¡o máº«u:

```text
WARNING: NgÆ°á»i láº¡ xuáº¥t hiá»‡n ngoÃ i giá» lÃ m viá»‡c
Camera: gate_01
Time: 20:42:11
Status: Unknown
```

---

### 8.2. Rule 2: NgÆ°á»i láº¡ láº£ng váº£ng á»Ÿ cá»•ng

Äiá»u kiá»‡n:

```text
Unknown Ä‘á»©ng trong vÃ¹ng cá»•ng hÆ¡n 10 giÃ¢y
```

Logic:

```python
if status == "unknown" and zone == "gate" and track_duration >= 10:
    warning_type = "unknown_loitering_at_gate"
    level = "medium"
```

Cáº§n cÃ³ tracking Ä‘á»ƒ biáº¿t Ä‘Ã¢y lÃ  cÃ¹ng má»™t ngÆ°á»i Ä‘ang Ä‘á»©ng lÃ¢u, khÃ´ng pháº£i nhiá»u ngÆ°á»i khÃ¡c nhau.

---

### 8.3. Rule 3: NgÆ°á»i láº¡ vÃ o khu vá»±c háº¡n cháº¿

VÃ­ dá»¥ khu vá»±c háº¡n cháº¿:

- PhÃ²ng server.
- Kho hÃ ng.
- Khu vá»±c tÃ i sáº£n.
- HÃ nh lang ná»™i bá»™.
- Cá»­a sau.
- BÃ£i xe sau giá» lÃ m.

Logic:

```python
if status == "unknown" and zone in RESTRICTED_ZONES:
    warning_type = "unknown_entered_restricted_area"
    level = "critical"
```

---

### 8.4. Rule 4: NgÆ°á»i láº¡ xuáº¥t hiá»‡n nhiá»u láº§n trong thá»i gian ngáº¯n

VÃ­ dá»¥:

```text
Unknown xuáº¥t hiá»‡n >= 3 láº§n trong 5 phÃºt
```

Logic:

```python
if unknown_count_in_5_minutes >= 3:
    warning_type = "repeated_unknown_appearance"
    level = "medium"
```

---

### 8.5. Rule 5: Unverified nhÆ°ng xuáº¥t hiá»‡n á»Ÿ vÃ¹ng nháº¡y cáº£m

TrÆ°á»ng há»£p khÃ´ng tháº¥y rÃµ máº·t nhÆ°ng ngÆ°á»i Ä‘Ã³ xuáº¥t hiá»‡n á»Ÿ vÃ¹ng quan trá»ng:

```python
if status == "unverified" and zone in RESTRICTED_ZONES:
    warning_type = "unverified_person_in_restricted_area"
    level = "medium"
```

---

## 9. Cáº¥p Ä‘á»™ cáº£nh bÃ¡o Ä‘á» xuáº¥t

| Äiá»u kiá»‡n | Má»©c cáº£nh bÃ¡o |
|---|---|
| Unknown xuáº¥t hiá»‡n bÃ¬nh thÆ°á»ng trong giá» lÃ m | Low |
| Unknown Ä‘á»©ng á»Ÿ cá»•ng quÃ¡ 10 giÃ¢y | Medium |
| Unknown xuáº¥t hiá»‡n ngoÃ i giá» lÃ m viá»‡c | High |
| Unknown vÃ o khu vá»±c háº¡n cháº¿ | Critical |
| Unknown + ngoÃ i giá» + khu vá»±c háº¡n cháº¿ | Critical |
| Unverified vÃ o khu vá»±c háº¡n cháº¿ | Medium |

---

## 10. Tracking vÃ  Voting

### 10.1. VÃ¬ sao cáº§n tracking?

Náº¿u xá»­ lÃ½ tá»«ng frame riÃªng láº», há»‡ thá»‘ng cÃ³ thá»ƒ cáº£nh bÃ¡o liÃªn tá»¥c:

```text
Frame 1: Unknown
Frame 2: Unknown
Frame 3: Unknown
Frame 4: Unknown
```

Äiá»u nÃ y gÃ¢y spam cáº£nh bÃ¡o. Tracking giÃºp gom cÃ¡c frame thuá»™c cÃ¹ng má»™t ngÆ°á»i thÃ nh má»™t `track_id`.

### 10.2. Tracking ID

VÃ­ dá»¥:

```text
Track ID 12:
- Frame 1: Unknown
- Frame 2: Unknown
- Frame 3: Known: Nguyen Van A
- Frame 4: Known: Nguyen Van A
- Frame 5: Unknown
```

Sau khi voting:

```text
Track ID 12 = Nguyen Van A
```

### 10.3. Voting theo nhiá»u frame

KhÃ´ng nÃªn káº¿t luáº­n báº±ng 1 frame. NÃªn dÃ¹ng nhiá»u frame.

VÃ­ dá»¥:

```text
Trong 30 frame:
- 22 frame nháº­n lÃ  Nguyen Van A
- 8 frame unknown

Káº¿t luáº­n: Nguyen Van A
```

Hoáº·c:

```text
Trong 30 frame:
- 25 frame unknown
- 0 frame known Ä‘á»§ threshold

Káº¿t luáº­n: Unknown
```

### 10.4. Gá»£i Ã½ rule voting

```python
if known_count >= 5 and best_known_score >= FACE_THRESHOLD:
    final_status = "known"
elif unknown_count >= 10 and known_count == 0:
    final_status = "unknown"
else:
    final_status = "unverified"
```

---

## 11. Khu vá»±c giÃ¡m sÃ¡t báº±ng ROI / Zone

Cáº§n Ä‘á»‹nh nghÄ©a cÃ¡c vÃ¹ng quan trá»ng trong camera.

VÃ­ dá»¥:

```text
gate_zone
door_zone
server_room_zone
warehouse_zone
parking_zone
restricted_zone
```

CÃ³ thá»ƒ Ä‘á»‹nh nghÄ©a báº±ng polygon:

```python
zones = {
    "gate": [(100, 200), (500, 200), (520, 600), (80, 600)],
    "restricted_area": [(600, 100), (900, 100), (900, 500), (600, 500)]
}
```

Kiá»ƒm tra ngÆ°á»i cÃ³ náº±m trong vÃ¹ng hay khÃ´ng báº±ng Ä‘iá»ƒm trung tÃ¢m bbox:

```python
center_x = (x1 + x2) / 2
center_y = (y1 + y2) / 2
```

Náº¿u Ä‘iá»ƒm trung tÃ¢m náº±m trong polygon thÃ¬ xem nhÆ° ngÆ°á»i Ä‘Ã³ Ä‘ang á»Ÿ vÃ¹ng tÆ°Æ¡ng á»©ng.

---

## 12. Snapshot vÃ  Log

Khi cÃ³ cáº£nh bÃ¡o, há»‡ thá»‘ng nÃªn lÆ°u:

- áº¢nh full frame.
- áº¢nh crop face.
- áº¢nh crop person náº¿u cÃ³ person detection.
- Thá»i gian.
- Camera ID.
- Track ID.
- Zone.
- Status.
- Best match gáº§n nháº¥t.
- Best score.
- Loáº¡i cáº£nh bÃ¡o.
- Má»©c cáº£nh bÃ¡o.

VÃ­ dá»¥ log:

```json
{
  "event_id": "EVT_20260519_204211_001",
  "track_id": 15,
  "camera_id": "gate_01",
  "time": "2026-05-19 20:42:11",
  "zone": "gate",
  "status": "unknown",
  "best_match_name": "Nguyen Van A",
  "best_score": 0.38,
  "warning_type": "unknown_outside_working_hours",
  "warning_level": "high",
  "snapshot_full": "snapshots/unknown/EVT_20260519_204211_001_full.jpg",
  "snapshot_face": "snapshots/unknown/EVT_20260519_204211_001_face.jpg"
}
```

---

## 13. Cáº¥u trÃºc thÆ° má»¥c gá»£i Ã½

```text
unknown_detection_system/
â”œâ”€â”€ main.py
â”œâ”€â”€ config.py
â”œâ”€â”€ insightface_detector.py
â”œâ”€â”€ insightface_recognizer.py
â”œâ”€â”€ qdrant_service.py
â”œâ”€â”€ recognition.py
â”œâ”€â”€ tracker.py
â”œâ”€â”€ zone_manager.py
â”œâ”€â”€ rule_engine.py
â”œâ”€â”€ alert_manager.py
â”œâ”€â”€ logger_service.py
â”œâ”€â”€ utils/
â”‚   â”œâ”€â”€ image_utils.py
â”‚   â”œâ”€â”€ time_utils.py
â”‚   â””â”€â”€ geometry_utils.py
â”œâ”€â”€ snapshots/
â”‚   â”œâ”€â”€ unknown/
â”‚   â”œâ”€â”€ unverified/
â”‚   â””â”€â”€ warnings/
â”œâ”€â”€ logs/
â”‚   â””â”€â”€ events.jsonl
â””â”€â”€ README.md
```

---

## 14. File config Ä‘á» xuáº¥t

```python
# config.py

INSIGHTFACE_DETECTION_MODEL = "<local-detection-model>"
INSIGHTFACE_RECOGNITION_MODEL = "<local-recognition-model>"
INSIGHTFACE_DEVICE = "cuda"  # hoáº·c "cpu" náº¿u mÃ¡y khÃ´ng cÃ³ GPU

QDRANT_HOST = "<qdrant-ip>"
QDRANT_PORT = 6333
QDRANT_COLLECTION = "employees_face"

FACE_THRESHOLD = 0.60

MIN_FACE_WIDTH = 60
MIN_FACE_HEIGHT = 60
MIN_DETECTION_SCORE = 0.75

WORKING_HOUR_START = "08:00"
WORKING_HOUR_END = "17:30"

LOITERING_SECONDS = 10
UNKNOWN_COUNT_WINDOW_SECONDS = 300
UNKNOWN_COUNT_THRESHOLD = 3

RESTRICTED_ZONES = [
    "server_room",
    "warehouse",
    "restricted_area"
]
```

---

## 15. Phase triá»ƒn khai chi tiáº¿t

## Phase 0: Chuáº©n bá»‹ mÃ´i trÆ°á»ng cháº¡y InsightFace local

### Má»¥c tiÃªu

MÃ¡y cá»§a mÃ¬nh cháº¡y Ä‘Æ°á»£c model InsightFace local cho detection vÃ  recognition.

### Viá»‡c cáº§n lÃ m

- CÃ i mÃ´i trÆ°á»ng Python, OpenCV, InsightFace vÃ  runtime phÃ¹ há»£p.
- Chá»n backend cháº¡y model: GPU náº¿u cÃ³ CUDA, CPU náº¿u khÃ´ng cÃ³ GPU.
- Táº£i hoáº·c cáº¥u hÃ¬nh model detection tá»« InsightFace.
- Táº£i hoáº·c cáº¥u hÃ¬nh model recognition tá»« InsightFace.
- Cháº¡y thá»­ detection trÃªn má»™t áº£nh máº·t.
- Cháº¡y thá»­ recognition Ä‘á»ƒ láº¥y embedding.
- Kiá»ƒm tra Qdrant Ä‘ang cháº¡y á»Ÿ Ä‘Ã¢u.
- Kiá»ƒm tra collection trong Qdrant tÃªn gÃ¬.
- Kiá»ƒm tra vector size.
- Kiá»ƒm tra metric Ä‘ang dÃ¹ng: cosine, dot hoáº·c euclidean.
- Kiá»ƒm tra payload trong Qdrant cÃ³ tÃªn nhÃ¢n viÃªn chÆ°a.

### Output

- MÃ¡y local detect Ä‘Æ°á»£c khuÃ´n máº·t.
- MÃ¡y local extract Ä‘Æ°á»£c embedding.
- CÃ³ thÃ´ng tin Qdrant.
- Biáº¿t collection, vector size, metric.
- Biáº¿t payload cÃ³ nhá»¯ng trÆ°á»ng nÃ o.

### Checklist

- [ ] InsightFace detection cháº¡y local thÃ nh cÃ´ng.
- [ ] InsightFace recognition cháº¡y local thÃ nh cÃ´ng.
- [ ] Embedding tráº£ vá» Ä‘Ãºng chiá»u.
- [ ] Káº¿t ná»‘i Ä‘Æ°á»£c tá»›i Qdrant.
- [ ] Query thá»­ má»™t embedding thÃ nh cÃ´ng.
- [ ] Láº¥y Ä‘Æ°á»£c tÃªn nhÃ¢n viÃªn tá»« payload.
- [ ] Biáº¿t threshold táº¡m thá»i Ä‘á»ƒ test.

---

## Phase 1: Káº¿t ná»‘i InsightFace local vÃ  Qdrant

### Má»¥c tiÃªu

MÃ¡y cá»§a mÃ¬nh tá»± detect máº·t, tá»± extract embedding báº±ng InsightFace local, sau Ä‘Ã³ query database Qdrant.

### Viá»‡c cáº§n lÃ m

- Viáº¿t `insightface_detector.py` Ä‘á»ƒ detect khuÃ´n máº·t trong áº£nh/frame.
- Viáº¿t `insightface_recognizer.py` Ä‘á»ƒ láº¥y embedding tá»« face crop/aligned face.
- Viáº¿t `qdrant_service.py` Ä‘á»ƒ query embedding.
- Láº¥y top-1 hoáº·c top-5 match.
- In ra káº¿t quáº£ match gá»“m:
  - employee_id
  - name
  - score

### Output

CÃ³ script test:

```text
Input: áº£nh gá»‘c
Output:
- Face bbox
- Best match
- Name
- Score
- Known / Unknown
```

### Checklist

- [ ] Detect Ä‘Æ°á»£c máº·t tá»« áº£nh gá»‘c.
- [ ] Crop/align face Ä‘Ãºng.
- [ ] Extract embedding local Ä‘Ãºng chiá»u.
- [ ] Query Qdrant thÃ nh cÃ´ng.
- [ ] Láº¥y Ä‘Æ°á»£c top result.
- [ ] So sÃ¡nh Ä‘Æ°á»£c vá»›i threshold.
- [ ] In ra Known / Unknown.

---

## Phase 2: Nháº­n diá»‡n Known / Unknown trÃªn áº£nh tÄ©nh

### Má»¥c tiÃªu

Test nháº­n diá»‡n ngÆ°á»i quen / ngÆ°á»i láº¡ trÃªn áº£nh trÆ°á»›c khi cháº¡y realtime.

### Viá»‡c cáº§n lÃ m

- Chuáº©n bá»‹ áº£nh nhÃ¢n viÃªn.
- Chuáº©n bá»‹ áº£nh ngÆ°á»i láº¡.
- Viáº¿t module `recognition.py`.
- Kiá»ƒm tra cháº¥t lÆ°á»£ng máº·t:
  - Face size.
  - Detection score.
  - Blur náº¿u cáº§n.
- Náº¿u match vÆ°á»£t threshold thÃ¬ Known.
- Náº¿u khÃ´ng vÆ°á»£t threshold thÃ¬ Unknown.
- Náº¿u áº£nh khÃ´ng Ä‘á»§ cháº¥t lÆ°á»£ng thÃ¬ Unverified.

### Output

Káº¿t quáº£ cho má»—i áº£nh:

```text
Image: test_001.jpg
Status: Known
Name: Nguyen Van A
Score: 0.72
```

Hoáº·c:

```text
Image: unknown_001.jpg
Status: Unknown
Best candidate: Tran Van B
Score: 0.41
```

### Checklist

- [ ] Nháº­n diá»‡n áº£nh nhÃ¢n viÃªn Ä‘Ãºng.
- [ ] áº¢nh ngÆ°á»i láº¡ tráº£ vá» Unknown.
- [ ] áº¢nh má»/nhá» tráº£ vá» Unverified.
- [ ] CÃ³ log káº¿t quáº£ test.
- [ ] CÃ³ thá»‘ng kÃª threshold sÆ¡ bá»™.

---

## Phase 3: Cháº¡y realtime camera vÃ  váº½ bounding box

### Má»¥c tiÃªu

Xá»­ lÃ½ video/camera realtime vÃ  hiá»ƒn thá»‹ káº¿t quáº£.

### Viá»‡c cáº§n lÃ m

- Má»Ÿ camera RTSP hoáº·c RTSP báº±ng OpenCV.
- Detect face trong tá»«ng frame báº±ng InsightFace detection local.
- Crop/align face.
- Extract embedding báº±ng InsightFace recognition local.
- Query Qdrant.
- Váº½ bounding box:
  - Known: khung xanh + tÃªn.
  - Unknown: khung Ä‘á» + Unknown.
  - Unverified: khung vÃ ng/xÃ¡m + Unverified.
- Hiá»ƒn thá»‹ score náº¿u cáº§n debug.

### Output

Giao diá»‡n realtime cÃ³:

```text
[Green box] Nguyen Van A - 0.72
[Red box] Unknown - 0.38
[Yellow box] Unverified
```

### Checklist

- [ ] Camera cháº¡y á»•n Ä‘á»‹nh.
- [ ] Bounding box hiá»ƒn thá»‹ Ä‘Ãºng.
- [ ] Known hiá»ƒn thá»‹ tÃªn tá»« DB.
- [ ] Unknown hiá»ƒn thá»‹ khung Ä‘á».
- [ ] KhÃ´ng cháº¡y detection/recognition quÃ¡ dÃ y gÃ¢y lag.
- [ ] FPS á»Ÿ má»©c cháº¥p nháº­n Ä‘Æ°á»£c.

---

## Phase 4: ThÃªm Tracking vÃ  Voting

### Má»¥c tiÃªu

Giáº£m cáº£nh bÃ¡o sai vÃ  trÃ¡nh spam cáº£nh bÃ¡o theo tá»«ng frame.

### Viá»‡c cáº§n lÃ m

- TÃ­ch há»£p tracking.
- GÃ¡n `track_id` cho má»—i ngÆ°á»i/khuÃ´n máº·t.
- LÆ°u lá»‹ch sá»­ nháº­n diá»‡n theo tá»«ng `track_id`.
- Voting nhiá»u frame Ä‘á»ƒ quyáº¿t Ä‘á»‹nh final status.
- Chá»‰ cáº£nh bÃ¡o khi track Ä‘Ã£ á»•n Ä‘á»‹nh.

### Output

Má»—i ngÆ°á»i trong video cÃ³ má»™t track riÃªng:

```text
Track ID 12:
Status: Known
Name: Nguyen Van A
Score avg: 0.68
```

Hoáº·c:

```text
Track ID 15:
Status: Unknown
Unknown frames: 20
Duration: 12 seconds
```

### Checklist

- [ ] CÃ³ track_id cho tá»«ng ngÆ°á»i.
- [ ] KhÃ´ng cáº£nh bÃ¡o láº·p liÃªn tá»¥c má»—i frame.
- [ ] Voting giÃºp giáº£m nháº§m Known thÃ nh Unknown.
- [ ] Track duration Ä‘Æ°á»£c tÃ­nh Ä‘Ãºng.
- [ ] Unknown chá»‰ Ä‘Æ°á»£c xÃ¡c nháº­n sau nhiá»u frame.

---

## Phase 5: XÃ¢y dá»±ng Zone / ROI

### Má»¥c tiÃªu

Biáº¿t ngÆ°á»i láº¡ Ä‘ang á»Ÿ khu vá»±c nÃ o Ä‘á»ƒ Ã¡p dá»¥ng rule cáº£nh bÃ¡o.

### Viá»‡c cáº§n lÃ m

- Äá»‹nh nghÄ©a polygon cho tá»«ng vÃ¹ng.
- Viáº¿t `zone_manager.py`.
- Kiá»ƒm tra bbox center cÃ³ náº±m trong vÃ¹ng nÃ o.
- GÃ¡n zone cho tá»«ng track.

### Output

Má»—i track cÃ³ zone:

```json
{
  "track_id": 15,
  "status": "unknown",
  "zone": "gate",
  "duration": 12
}
```

### Checklist

- [ ] Äá»‹nh nghÄ©a Ä‘Æ°á»£c vÃ¹ng cá»•ng.
- [ ] Äá»‹nh nghÄ©a Ä‘Æ°á»£c vÃ¹ng háº¡n cháº¿.
- [ ] Detect Ä‘Ãºng ngÆ°á»i Ä‘ang á»Ÿ zone nÃ o.
- [ ] CÃ³ thá»ƒ cáº¥u hÃ¬nh zone theo tá»«ng camera.
- [ ] CÃ³ thá»ƒ báº­t/táº¯t rule theo zone.

---

## Phase 6: XÃ¢y dá»±ng Rule Engine cáº£nh bÃ¡o

### Má»¥c tiÃªu

Cáº£nh bÃ¡o khi Unknown cÃ³ Ä‘iá»u kiá»‡n Ä‘Ã¡ng ngá».

### Viá»‡c cáº§n lÃ m

- Viáº¿t `rule_engine.py`.
- Kiá»ƒm tra rule ngoÃ i giá».
- Kiá»ƒm tra rule láº£ng váº£ng á»Ÿ cá»•ng.
- Kiá»ƒm tra rule vÃ o khu vá»±c cáº¥m.
- Kiá»ƒm tra rule xuáº¥t hiá»‡n nhiá»u láº§n.
- GÃ¡n warning level.

### Output

Sá»± kiá»‡n cáº£nh bÃ¡o:

```text
[HIGH] Unknown person outside working hours
Camera: gate_01
Zone: gate
Time: 20:42:11
```

### Checklist

- [ ] Unknown trong giá» lÃ m khÃ´ng bá»‹ cáº£nh bÃ¡o quÃ¡ má»©c.
- [ ] Unknown ngoÃ i giá» cÃ³ warning.
- [ ] Unknown Ä‘á»©ng lÃ¢u á»Ÿ cá»•ng cÃ³ warning.
- [ ] Unknown vÃ o vÃ¹ng cáº¥m cÃ³ warning.
- [ ] CÃ³ phÃ¢n cáº¥p Low / Medium / High / Critical.
- [ ] KhÃ´ng spam cáº£nh bÃ¡o liÃªn tá»¥c.

---

## Phase 7: Snapshot, Log vÃ  Dashboard

### Má»¥c tiÃªu

LÆ°u láº¡i báº±ng chá»©ng vÃ  hiá»ƒn thá»‹ cáº£nh bÃ¡o.

### Viá»‡c cáº§n lÃ m

- Viáº¿t `alert_manager.py`.
- Khi cÃ³ warning:
  - LÆ°u full frame.
  - LÆ°u face crop.
  - LÆ°u person crop náº¿u cÃ³.
  - Ghi log vÃ o JSONL/database.
- Hiá»ƒn thá»‹ danh sÃ¡ch cáº£nh bÃ¡o trÃªn dashboard.
- CÃ³ thá»ƒ gá»­i Telegram/Email náº¿u cáº§n.

### Output

ThÆ° má»¥c snapshot:

```text
snapshots/
â”œâ”€â”€ unknown/
â”‚   â””â”€â”€ UNK_20260519_204211_face.jpg
â””â”€â”€ warnings/
    â””â”€â”€ EVT_20260519_204211_full.jpg
```

Log sá»± kiá»‡n:

```json
{
  "event_id": "EVT_20260519_204211_001",
  "camera_id": "gate_01",
  "track_id": 15,
  "status": "unknown",
  "zone": "gate",
  "warning_type": "unknown_outside_working_hours",
  "warning_level": "high",
  "snapshot_full": "snapshots/warnings/EVT_20260519_204211_full.jpg"
}
```

### Checklist

- [ ] CÃ³ lÆ°u áº£nh khi warning.
- [ ] CÃ³ log Ä‘áº§y Ä‘á»§ thÃ´ng tin.
- [ ] CÃ³ thá»ƒ xem láº¡i cáº£nh bÃ¡o.
- [ ] CÃ³ thá»ƒ debug score vÃ  best match.
- [ ] CÃ³ thá»ƒ xuáº¥t bÃ¡o cÃ¡o náº¿u cáº§n.

---

## Phase 8: Test, Ä‘Ã¡nh giÃ¡ vÃ  tinh chá»‰nh

### Má»¥c tiÃªu

ÄÃ¡nh giÃ¡ há»‡ thá»‘ng trong mÃ´i trÆ°á»ng tháº­t vÃ  giáº£m lá»—i.

### Viá»‡c cáº§n lÃ m

- Test vá»›i nhÃ¢n viÃªn tháº­t.
- Test vá»›i ngÆ°á»i khÃ´ng cÃ³ trong database.
- Test trong giá» lÃ m.
- Test ngoÃ i giá» lÃ m.
- Test á»Ÿ cá»•ng.
- Test á»Ÿ khu vá»±c háº¡n cháº¿.
- Test Ã¡nh sÃ¡ng yáº¿u.
- Test máº·t nghiÃªng, Ä‘eo kháº©u trang, Ä‘i nhanh.
- Äiá»u chá»‰nh threshold.
- Äiá»u chá»‰nh thá»i gian loitering.
- Äiá»u chá»‰nh rule warning.

### Chá»‰ sá»‘ Ä‘Ã¡nh giÃ¡

| Chá»‰ sá»‘ | Ã nghÄ©a |
|---|---|
| Known accuracy | Tá»‰ lá»‡ nháº­n Ä‘Ãºng nhÃ¢n viÃªn |
| Unknown detection rate | Tá»‰ lá»‡ phÃ¡t hiá»‡n Ä‘Ãºng ngÆ°á»i láº¡ |
| False accept | NgÆ°á»i láº¡ bá»‹ nháº­n nháº§m thÃ nh nhÃ¢n viÃªn |
| False reject | NhÃ¢n viÃªn bá»‹ nháº­n nháº§m thÃ nh Unknown |
| Warning precision | Cáº£nh bÃ¡o cÃ³ Ä‘Ãºng khÃ´ng |
| Warning spam rate | CÃ³ bá»‹ cáº£nh bÃ¡o quÃ¡ nhiá»u khÃ´ng |
| Processing FPS | Tá»‘c Ä‘á»™ xá»­ lÃ½ realtime |

### Checklist

- [ ] Test Ä‘á»§ nhÃ¢n viÃªn.
- [ ] Test Ä‘á»§ ngÆ°á»i láº¡.
- [ ] CÃ³ báº£ng káº¿t quáº£ threshold.
- [ ] CÃ³ thá»‘ng kÃª lá»—i.
- [ ] Tinh chá»‰nh rule cáº£nh bÃ¡o.
- [ ] Cháº¡y thá»­ á»•n Ä‘á»‹nh trong nhiá»u giá».

---

## 16. Pseudocode tá»•ng thá»ƒ

```python
for frame in camera_stream:
    faces = detect_faces(frame)

    for face in faces:
        face_crop = crop_face(frame, face.bbox)

        if not is_good_quality_face(face):
            status = "unverified"
            label = "Unverified"
            score = None
        else:
            aligned_face = insightface_detector.align(frame, face)
            embedding = insightface_recognizer.extract_embedding(aligned_face)
            search_result = qdrant_service.search(embedding, top_k=5)

            best_match = search_result[0]
            best_score = best_match.score

            if best_score >= FACE_THRESHOLD:
                status = "known"
                label = best_match.payload["name"]
            else:
                status = "unknown"
                label = "Unknown"

        track_id = tracker.update(face.bbox)

        tracker.update_recognition_history(
            track_id=track_id,
            status=status,
            label=label,
            score=score
        )

        final_status = tracker.get_voted_status(track_id)

        zone = zone_manager.get_zone(face.bbox)

        warning = rule_engine.check(
            track_id=track_id,
            status=final_status,
            zone=zone,
            current_time=now(),
            duration=tracker.get_duration(track_id)
        )

        if warning.should_alert:
            alert_manager.save_snapshot(
                frame=frame,
                face_crop=face_crop,
                track_id=track_id,
                warning=warning
            )

            alert_manager.write_log(
                track_id=track_id,
                status=final_status,
                zone=zone,
                warning=warning
            )

        draw_box(
            frame=frame,
            bbox=face.bbox,
            label=label,
            status=final_status
        )
```

---

## 17. Roadmap ngáº¯n gá»n

```text
Phase 0: Chuáº©n bá»‹ mÃ´i trÆ°á»ng InsightFace local
Phase 1: Káº¿t ná»‘i InsightFace local + Qdrant
Phase 2: Nháº­n diá»‡n Known / Unknown trÃªn áº£nh tÄ©nh
Phase 3: Cháº¡y realtime camera + bounding box
Phase 4: ThÃªm tracking + voting
Phase 5: ThÃªm zone / ROI
Phase 6: ThÃªm rule engine cáº£nh bÃ¡o
Phase 7: LÆ°u snapshot + log + dashboard
Phase 8: Test thá»±c táº¿ + tinh chá»‰nh threshold/rule
```

---

## 18. Káº¿t luáº­n

HÆ°á»›ng triá»ƒn khai há»£p lÃ½ nháº¥t lÃ  xÃ¢y há»‡ thá»‘ng theo mÃ´ hÃ¬nh:

```text
InsightFace local detection + InsightFace local recognition + Qdrant DB + Unknown Detection + Rule Engine + Snapshot/Log
```

Trong Ä‘Ã³:

- NgÆ°á»i cÃ³ trong database: hiá»ƒn thá»‹ khung xanh vÃ  tÃªn.
- NgÆ°á»i khÃ´ng cÃ³ trong database: hiá»ƒn thá»‹ khung Ä‘á» vÃ  Unknown.
- NgÆ°á»i khÃ´ng Ä‘á»§ cháº¥t lÆ°á»£ng nháº­n diá»‡n: hiá»ƒn thá»‹ Unverified.
- Unknown chá»‰ cáº£nh bÃ¡o khi cÃ³ Ä‘iá»u kiá»‡n Ä‘Ã¡ng ngá»:
  - NgoÃ i giá» lÃ m viá»‡c.
  - Láº£ng váº£ng á»Ÿ cá»•ng.
  - VÃ o khu vá»±c háº¡n cháº¿.
  - Xuáº¥t hiá»‡n nhiá»u láº§n.

Äiá»ƒm quan trá»ng nháº¥t khi triá»ƒn khai thá»±c táº¿:

- KhÃ´ng cáº£nh bÃ¡o chá»‰ dá»±a trÃªn 1 frame.
- Cáº§n tracking vÃ  voting theo nhiá»u frame.
- Cáº§n chá»n threshold báº±ng dá»¯ liá»‡u camera tháº­t.
- Cáº§n lÆ°u log vÃ  snapshot Ä‘á»ƒ debug.
- Cáº§n tÃ¡ch rÃµ nháº­n diá»‡n vÃ  cáº£nh bÃ¡o thÃ nh hai module riÃªng.

---

## 19. Plan dá»±ng há»‡ thá»‘ng theo tá»«ng phase

Pháº§n nÃ y lÃ  plan triá»ƒn khai thá»±c táº¿ Ä‘á»ƒ dá»±ng há»‡ thá»‘ng tá»« dá»¯ liá»‡u hiá»‡n cÃ³. Má»¥c tiÃªu lÃ  Ä‘i tá»«ng phase nhá», má»—i phase cÃ³ output kiá»ƒm chá»©ng Ä‘Æ°á»£c trÆ°á»›c khi qua phase tiáº¿p theo.

### Dá»¯ liá»‡u hiá»‡n cÃ³

```text
manifest_20260521T080719Z.json
        â†“
XÃ¡c nháº­n bá»™ export gá»“m Postgres + Qdrant

postgres_20260521T080719Z.json
        â†“
Database nghiá»‡p vá»¥ face_db
        â†“
Báº£ng employees chá»©a thÃ´ng tin nhÃ¢n viÃªn:
- id
- emp_code
- name
- department
- photo_path
- is_active

qdrant_20260521T080719Z.json
        â†“
Vector database
        â†“
Collection employee_faces:
- vector size: 512
- distance: Cosine
- points_count: 44
- payload cÃ³ employee_id, emp_code, name, department, is_active
```

### Pipeline tá»•ng thá»ƒ cáº§n dá»±ng

```text
Camera / Video / Image
        â†“
Frame Reader
        â†“
InsightFace Detection local
        â†“
Face bbox + landmarks + detection score
        â†“
Face quality check
        â†“
Crop / align face
        â†“
InsightFace Recognition local
        â†“
512-d embedding
        â†“
Normalize embedding Ä‘Ãºng cÃ¡ch
        â†“
Qdrant search trong collection employee_faces
        â†“
Top-k candidates
        â†“
Recognition Decision
        â†“
Known / Unknown / Unverified
        â†“
Tracking + Voting theo track_id
        â†“
Zone / ROI check
        â†“
Rule Engine
        â†“
Alert / Snapshot / Log
```

### Phase 0: KhÃ³a schema vÃ  dá»¯ liá»‡u ná»n

#### Má»¥c tiÃªu

Hiá»ƒu cháº¯c dá»¯ liá»‡u Postgres, Qdrant vÃ  manifest trÆ°á»›c khi viáº¿t pipeline xá»­ lÃ½ áº£nh.

#### Viá»‡c cáº§n lÃ m

- Äá»c `manifest_20260521T080719Z.json` Ä‘á»ƒ xÃ¡c nháº­n bá»™ export.
- Äá»c schema Postgres, táº­p trung trÆ°á»›c vÃ o báº£ng `employees`.
- Äá»c schema Qdrant, táº­p trung trÆ°á»›c vÃ o collection `employee_faces`.
- XÃ¡c nháº­n mapping giá»¯a Qdrant payload vÃ  Postgres:
  - `payload.employee_id` â†” `employees.id`
  - `payload.emp_code` â†” `employees.emp_code`
  - `payload.name` â†” `employees.name`
- XÃ¡c nháº­n vector size lÃ  `512` vÃ  distance lÃ  `Cosine`.
- XÃ¡c nháº­n chá»‰ dÃ¹ng nhÃ¢n viÃªn `is_active = true` khi nháº­n diá»‡n.

#### Output cáº§n cÃ³

```text
Data contract:
- employee_id láº¥y tá»« Qdrant payload
- name láº¥y tá»« Qdrant payload hoáº·c join Postgres employees
- vector size báº¯t buá»™c 512
- metric báº¯t buá»™c Cosine
```

#### Äiá»u kiá»‡n qua phase

- [ ] Biáº¿t collection Qdrant chÃ­nh xÃ¡c: `employee_faces`.
- [ ] Biáº¿t báº£ng Postgres chÃ­nh xÃ¡c: `employees`.
- [ ] Biáº¿t key mapping giá»¯a Qdrant vÃ  Postgres.
- [ ] KhÃ´ng cÃ²n mÆ¡ há»“ embedding má»›i pháº£i cÃ³ shape bao nhiÃªu.

---

### Phase 1: Dá»±ng project skeleton tá»‘i thiá»ƒu

#### Má»¥c tiÃªu

Táº¡o bá»™ khung code nhá», chÆ°a xá»­ lÃ½ realtime, chá»‰ Ä‘á»§ Ä‘á»ƒ test tá»«ng module Ä‘á»™c láº­p.

#### Cáº¥u trÃºc Ä‘á» xuáº¥t

```text
unknown_detection_system/
â”œâ”€â”€ main.py
â”œâ”€â”€ config.py
â”œâ”€â”€ data_contract.py
â”œâ”€â”€ insightface_detector.py
â”œâ”€â”€ insightface_recognizer.py
â”œâ”€â”€ face_pipeline.py
â”œâ”€â”€ qdrant_service.py
â”œâ”€â”€ postgres_service.py
â”œâ”€â”€ recognition_decision.py
â”œâ”€â”€ tests_manual/
â”‚   â”œâ”€â”€ test_qdrant_search.py
â”‚   â”œâ”€â”€ test_postgres_lookup.py
â”‚   â”œâ”€â”€ test_detect_image.py
â”‚   â””â”€â”€ test_recognize_image.py
â””â”€â”€ outputs/
    â”œâ”€â”€ debug_faces/
    â””â”€â”€ logs/
```

#### Pipeline trong phase nÃ y

```text
Config
  â†“
Load Qdrant/Postgres connection info
  â†“
Load InsightFace model config
  â†“
Cháº¡y tá»«ng script test Ä‘á»™c láº­p
```

#### Äiá»u kiá»‡n qua phase

- [ ] CÃ³ `config.py` chá»©a tÃªn collection, threshold, device, model path/name.
- [ ] CÃ³ module Qdrant service nhÆ°ng chá»‰ search thá»­, chÆ°a ná»‘i camera.
- [ ] CÃ³ module Postgres service nhÆ°ng chá»‰ lookup nhÃ¢n viÃªn, chÆ°a ghi log.
- [ ] CÃ³ module detector/recognizer nhÆ°ng chÆ°a realtime.

---

### Phase 2: Káº¿t ná»‘i vÃ  kiá»ƒm thá»­ Qdrant/Postgres trÆ°á»›c

#### Má»¥c tiÃªu

Äáº£m báº£o pháº§n DB hoáº¡t Ä‘á»™ng Ä‘Ãºng trÆ°á»›c khi Ä‘á»¥ng model áº£nh.

#### Pipeline kiá»ƒm thá»­

```text
Láº¥y 1 vector cÃ³ sáºµn tá»« qdrant export
        â†“
Search láº¡i vÃ o Qdrant collection employee_faces
        â†“
Nháº­n top-k candidates
        â†“
Láº¥y employee_id / emp_code / name tá»« payload
        â†“
Lookup Postgres employees náº¿u cáº§n bá»• sung thÃ´ng tin
        â†“
In káº¿t quáº£ kiá»ƒm chá»©ng
```

#### Output mong muá»‘n

```text
Query vector id: 7
Top 1:
- employee_id: 7
- emp_code: NV011
- name: HoÃ ng Máº¡nh Tiáº¿n
- score: gáº§n 1.0 náº¿u search báº±ng chÃ­nh vector gá»‘c
```

#### Äiá»u kiá»‡n qua phase

- [ ] Query Qdrant thÃ nh cÃ´ng.
- [ ] Top-1 tráº£ vá» Ä‘Ãºng nhÃ¢n viÃªn khi dÃ¹ng vector gá»‘c.
- [ ] Payload cÃ³ Ä‘á»§ `employee_id`, `emp_code`, `name`.
- [ ] Lookup Postgres theo `employee_id` thÃ nh cÃ´ng náº¿u cáº§n.

---

### Phase 3: Cháº¡y InsightFace detection local trÃªn áº£nh tÄ©nh

#### Má»¥c tiÃªu

MÃ¡y local detect Ä‘Æ°á»£c khuÃ´n máº·t á»•n Ä‘á»‹nh trÆ°á»›c khi recognition.

#### Pipeline

```text
Input image
        â†“
OpenCV read image
        â†“
InsightFace detection local
        â†“
List face bbox + landmarks + det_score
        â†“
Filter theo MIN_DETECTION_SCORE, MIN_FACE_WIDTH, MIN_FACE_HEIGHT
        â†“
Save áº£nh debug cÃ³ bbox
```

#### Output mong muá»‘n

```text
Image: test_employee.jpg
Faces detected: 1
Face 1:
- bbox: [x1, y1, x2, y2]
- det_score: 0.92
- quality: pass
```

#### Äiá»u kiá»‡n qua phase

- [ ] Detect Ä‘Æ°á»£c máº·t trÃªn áº£nh nhÃ¢n viÃªn rÃµ.
- [ ] KhÃ´ng nháº­n máº·t quÃ¡ nhá»/má» náº¿u dÆ°á»›i ngÆ°á»¡ng.
- [ ] LÆ°u Ä‘Æ°á»£c áº£nh debug bbox Ä‘á»ƒ nhÃ¬n báº±ng máº¯t.
- [ ] Biáº¿t FPS detection táº¡m thá»i trÃªn mÃ¡y local.

---

### Phase 4: Cháº¡y InsightFace recognition local vÃ  kiá»ƒm tra embedding

#### Má»¥c tiÃªu

Tá»« bbox Ä‘Ã£ detect, extract Ä‘Æ°á»£c embedding 512 chiá»u Ä‘Ãºng chuáº©n.

#### Pipeline

```text
Input image
        â†“
Detection
        â†“
Landmarks
        â†“
Align face
        â†“
Recognition model local
        â†“
Embedding 512-d
        â†“
Normalize embedding
        â†“
Kiá»ƒm tra shape + norm
```

#### Output mong muá»‘n

```text
Embedding shape: (512,)
Embedding norm: ~1.0 náº¿u Ä‘Ã£ normalize
```

#### Äiá»u kiá»‡n qua phase

- [ ] Extract Ä‘Æ°á»£c embedding tá»« áº£nh rÃµ máº·t.
- [ ] Embedding cÃ³ Ä‘Ãºng 512 chiá»u.
- [ ] CÃ¡ch normalize thá»‘ng nháº¥t vá»›i dá»¯ liá»‡u trong Qdrant.
- [ ] Náº¿u embedding search sai hoÃ n toÃ n, dá»«ng láº¡i kiá»ƒm tra model recognition cÃ³ trÃ¹ng model táº¡o DB khÃ´ng.

---

### Phase 5: Ná»‘i recognition local vá»›i Qdrant Ä‘á»ƒ phÃ¢n loáº¡i Known/Unknown

#### Má»¥c tiÃªu

áº¢nh tÄ©nh Ä‘i háº¿t pipeline tá»« áº£nh gá»‘c Ä‘áº¿n Known/Unknown.

#### Pipeline

```text
Input image
        â†“
Detect face
        â†“
Quality check
        â†“
Align face
        â†“
Extract embedding
        â†“
Qdrant search top_k=5
        â†“
Best score
        â†“
Compare FACE_THRESHOLD
        â†“
Known / Unknown / Unverified
```

#### Logic quyáº¿t Ä‘á»‹nh

```python
if face_quality_is_low:
    status = "unverified"
elif best_score >= FACE_THRESHOLD:
    status = "known"
else:
    status = "unknown"
```

#### Output mong muá»‘n

```text
Image: sample.jpg
Status: known
Name: Nguyen Van A
Employee ID: 10
Score: 0.68
Best candidates:
1. Nguyen Van A - 0.68
2. Tran Van B - 0.42
3. Le Van C - 0.39
```

#### Äiá»u kiá»‡n qua phase

- [ ] áº¢nh nhÃ¢n viÃªn trong DB cÃ³ thá»ƒ ra Known.
- [ ] áº¢nh ngÆ°á»i ngoÃ i DB cÃ³ thá»ƒ ra Unknown.
- [ ] áº¢nh má»/nhá» ra Unverified.
- [ ] CÃ³ log top-k Ä‘á»ƒ debug threshold.

---

### Phase 6: Cháº¡y video/camera nhÆ°ng chÆ°a cáº£nh bÃ¡o

#### Má»¥c tiÃªu

ÄÆ°a pipeline áº£nh tÄ©nh vÃ o video realtime, chá»‰ váº½ bbox vÃ  label, chÆ°a Rule Engine.

#### Pipeline

```text
Camera / video file
        â†“
Read frame
        â†“
Skip frame náº¿u cáº§n Ä‘á»ƒ giáº£m lag
        â†“
Detect faces
        â†“
Recognition theo tá»«ng face Ä‘á»§ cháº¥t lÆ°á»£ng
        â†“
Qdrant search
        â†“
Draw bbox:
- Known: xanh + tÃªn
- Unknown: Ä‘á» + Unknown
- Unverified: vÃ ng/xÃ¡m + Unverified
        â†“
Show frame / save debug video
```

#### Äiá»u kiá»‡n qua phase

- [ ] Camera hoáº·c video cháº¡y á»•n Ä‘á»‹nh.
- [ ] KhÃ´ng crash khi khÃ´ng cÃ³ máº·t.
- [ ] KhÃ´ng lag quÃ¡ má»©c do cháº¡y recognition má»—i frame.
- [ ] CÃ³ thá»ƒ cáº¥u hÃ¬nh xá»­ lÃ½ má»—i N frame.
- [ ] Label vÃ  mÃ u bbox Ä‘Ãºng.

---

### Phase 7: ThÃªm tracking vÃ  voting

#### Má»¥c tiÃªu

KhÃ´ng káº¿t luáº­n ngÆ°á»i láº¡ dá»±a trÃªn má»™t frame Ä‘Æ¡n láº».

#### Pipeline

```text
Frame detections
        â†“
Tracker assign track_id
        â†“
LÆ°u recognition history theo track_id
        â†“
Voting nhiá»u frame
        â†“
Final status theo track:
- known
- unknown
- unverified
        â†“
Draw stable label
```

#### Rule voting ban Ä‘áº§u

```python
if known_count >= 5 and best_known_score >= FACE_THRESHOLD:
    final_status = "known"
elif unknown_count >= 10 and known_count == 0:
    final_status = "unknown"
else:
    final_status = "unverified"
```

#### Äiá»u kiá»‡n qua phase

- [ ] Má»—i ngÆ°á»i cÃ³ `track_id` á»•n Ä‘á»‹nh.
- [ ] KhÃ´ng nháº¥p nhÃ¡y Known/Unknown liÃªn tá»¥c.
- [ ] Unknown chá»‰ Ä‘Æ°á»£c xÃ¡c nháº­n sau nhiá»u frame.
- [ ] CÃ³ duration theo track.

---

### Phase 8: ThÃªm Zone / ROI

#### Má»¥c tiÃªu

Biáº¿t ngÆ°á»i láº¡ Ä‘ang á»Ÿ khu vá»±c nÃ o Ä‘á»ƒ phá»¥c vá»¥ cáº£nh bÃ¡o.

#### Pipeline

```text
Track bbox
        â†“
TÃ­nh center point hoáº·c foot point
        â†“
Check point náº±m trong polygon nÃ o
        â†“
GÃ¡n zone cho track
        â†“
ÄÆ°a zone vÃ o Rule Engine sau nÃ y
```

#### Äiá»u kiá»‡n qua phase

- [ ] Cáº¥u hÃ¬nh Ä‘Æ°á»£c zone theo camera.
- [ ] Váº½ Ä‘Æ°á»£c polygon zone lÃªn frame debug.
- [ ] Track Ä‘Æ°á»£c gÃ¡n Ä‘Ãºng zone.
- [ ] CÃ³ zone máº·c Ä‘á»‹nh lÃ  `none` náº¿u khÃ´ng náº±m trong vÃ¹ng nÃ o.

---

### Phase 9: ThÃªm Rule Engine cáº£nh bÃ¡o

#### Má»¥c tiÃªu

Chá»‰ cáº£nh bÃ¡o khi Unknown cÃ³ Ä‘iá»u kiá»‡n Ä‘Ã¡ng ngá», khÃ´ng spam khi vá»«a tháº¥y Unknown.

#### Pipeline

```text
Final track status
        â†“
Track duration
        â†“
Zone
        â†“
Current time
        â†“
Rule Engine
        â†“
Warning hoáº·c no warning
```

#### Rule ban Ä‘áº§u

```text
Rule 1: Unknown ngoÃ i giá» lÃ m viá»‡c â†’ High
Rule 2: Unknown Ä‘á»©ng á»Ÿ cá»•ng quÃ¡ N giÃ¢y â†’ Medium
Rule 3: Unknown vÃ o restricted zone â†’ Critical
Rule 4: Unknown xuáº¥t hiá»‡n nhiá»u láº§n trong M phÃºt â†’ Medium
Rule 5: Unverified vÃ o restricted zone â†’ Medium
```

#### Äiá»u kiá»‡n qua phase

- [ ] Unknown bÃ¬nh thÆ°á»ng trong giá» lÃ m khÃ´ng spam cáº£nh bÃ¡o.
- [ ] Unknown ngoÃ i giá» cÃ³ warning.
- [ ] Unknown á»Ÿ vÃ¹ng cáº¥m cÃ³ warning.
- [ ] CÃ³ cooldown theo `track_id` vÃ  `warning_type`.

---

### Phase 10: Snapshot, log vÃ  tÃ­ch há»£p Postgres

#### Má»¥c tiÃªu

Khi cÃ³ warning, lÆ°u báº±ng chá»©ng Ä‘á»ƒ xem láº¡i vÃ  debug.

#### Pipeline

```text
Warning event
        â†“
Generate event_id
        â†“
Save full frame
        â†“
Save face crop
        â†“
Build event payload
        â†“
Write JSONL log trÆ°á»›c
        â†“
Sau khi á»•n Ä‘á»‹nh má»›i ghi Postgres table riÃªng náº¿u cáº§n
```

#### Dá»¯ liá»‡u log tá»‘i thiá»ƒu

```json
{
  "event_id": "EVT_20260521_101530_001",
  "camera_id": "gate_01",
  "track_id": 15,
  "status": "unknown",
  "zone": "gate",
  "best_match_employee_id": 7,
  "best_match_name": "HoÃ ng Máº¡nh Tiáº¿n",
  "best_score": 0.38,
  "warning_type": "unknown_outside_working_hours",
  "warning_level": "high",
  "snapshot_full": "outputs/snapshots/EVT_20260521_101530_001_full.jpg",
  "snapshot_face": "outputs/snapshots/EVT_20260521_101530_001_face.jpg"
}
```

#### Äiá»u kiá»‡n qua phase

- [ ] CÃ³ snapshot full frame.
- [ ] CÃ³ snapshot face crop.
- [ ] CÃ³ JSONL log Ä‘á»c láº¡i Ä‘Æ°á»£c.
- [ ] KhÃ´ng ghi Postgres trá»±c tiáº¿p cho Ä‘áº¿n khi schema event á»•n Ä‘á»‹nh.

---

### Phase 11: Test thá»±c táº¿ vÃ  khÃ³a threshold

#### Má»¥c tiÃªu

Chá»n threshold vÃ  rule báº±ng dá»¯ liá»‡u camera tháº­t, khÃ´ng chá»n theo cáº£m tÃ­nh.

#### Pipeline Ä‘Ã¡nh giÃ¡

```text
Táº­p áº£nh/video nhÃ¢n viÃªn
        â†“
Táº­p áº£nh/video ngÆ°á»i láº¡
        â†“
Cháº¡y pipeline batch
        â†“
Ghi score, status, best candidate
        â†“
TÃ­nh false accept / false reject
        â†“
Äiá»u chá»‰nh FACE_THRESHOLD
        â†“
Cháº¡y láº¡i video realtime
```

#### Chá»‰ sá»‘ cáº§n theo dÃµi

```text
Known accuracy
Unknown detection rate
False accept
False reject
Warning precision
Warning spam rate
Processing FPS
```

#### Äiá»u kiá»‡n hoÃ n táº¥t báº£n dá»±ng Ä‘áº§u tiÃªn

- [ ] CÃ³ threshold táº¡m á»•n trÃªn dá»¯ liá»‡u camera tháº­t.
- [ ] FPS Ä‘á»§ dÃ¹ng trÃªn mÃ¡y local.
- [ ] Warning khÃ´ng spam.
- [ ] Snapshot/log Ä‘á»§ Ä‘á»ƒ truy váº¿t lá»—i.
- [ ] Biáº¿t rÃµ cÃ¡c case yáº¿u: thiáº¿u sÃ¡ng, máº·t nghiÃªng, kháº©u trang, motion blur.

---

### Thá»© tá»± lÃ m ngay tá»« bÃ¢y giá»

```text
1. Phase 0: KhÃ³a schema Qdrant/Postgres/manifest.
2. Phase 1: Dá»±ng skeleton project tá»‘i thiá»ƒu.
3. Phase 2: Test Qdrant/Postgres báº±ng vector cÃ³ sáºµn.
4. Phase 3: Test InsightFace detection local trÃªn áº£nh tÄ©nh.
5. Phase 4: Test InsightFace recognition local vÃ  embedding 512 chiá»u.
6. Phase 5: Ná»‘i áº£nh tÄ©nh â†’ Known/Unknown.
```

KhÃ´ng nÃªn nháº£y tháº³ng vÃ o realtime camera trÆ°á»›c khi Phase 2 Ä‘áº¿n Phase 5 cháº¡y á»•n, vÃ¬ náº¿u káº¿t quáº£ sai sáº½ ráº¥t khÃ³ biáº¿t lá»—i náº±m á»Ÿ model, embedding, threshold hay database.
