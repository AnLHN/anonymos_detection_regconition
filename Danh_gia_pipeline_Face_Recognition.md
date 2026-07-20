# Đánh giá và đề xuất cải tiến pipeline Face Recognition + Unknown Detection

## Đánh giá tổng quan

Kiến trúc hiện tại được đánh giá khoảng **8.8/10** và phù hợp cho hệ
thống AI camera realtime.

### Điểm mạnh

-   Chỉ chạy InsightFace detector **một lần** trên mỗi frame.
-   Tách riêng logic **Tracking** và **Recognition**.
-   Có hai ngưỡng detection:
    -   Tracking (`TRACK_DETECTION_SCORE`)
    -   Recognition (`RECOGNITION_DETECTION_SCORE`)
-   Không query Qdrant với các khuôn mặt chất lượng thấp.
-   Unknown chỉ tạo cảnh báo sau khi ổn định (stable).
-   Một track chỉ gửi một cảnh báo unknown.
-   Có cơ chế resolve khi người lạ sau đó được nhận diện thành người
    quen.

## Đánh giá các threshold

### Camera 1280x720

Do camera chạy ở độ phân giải 1280×720 nên:

-   `MIN_FACE_WIDTH = 40`
-   `MIN_FACE_HEIGHT = 40`

là hợp lý và không cần tăng lên 60--80 như với camera 1080p hoặc 4K.

Khuyến nghị:

``` env
TRACK_MIN_FACE_SIZE=30
RECOGNITION_MIN_FACE_SIZE=40
BEST_FACE_MIN_SIZE=60
```

Ý nghĩa:

-   =30 px: tracker.

-   =40 px: recognition.

-   =60 px: ưu tiên lưu best face.

## Những điểm nên cải thiện

### 1. Face Quality

Không nên chỉ dựa vào detection score.

Nên đánh giá thêm:

-   Blur
-   Pose (yaw/pitch/roll)
-   Brightness
-   Occlusion

Recognition chỉ thực hiện khi khuôn mặt đủ chất lượng.

### 2. Best Face Cache

Mỗi Track nên lưu:

``` python
best_face
best_embedding
best_quality
```

Khi frame mới có chất lượng tốt hơn thì cập nhật và dùng để query
Qdrant.

Điều này giúp tăng đáng kể độ chính xác khi người tiến lại gần camera.

### 3. Tracker

Centroid Tracker phù hợp cho môi trường đơn giản.

Nếu production hoặc nhiều người xuất hiện cùng lúc, nên chuyển sang:

-   ByteTrack (khuyến nghị)
-   DeepSORT
-   BoT-SORT

### 4. Unknown Stable

Nên dùng thời gian thay vì số frame.

Ví dụ:

``` text
UNKNOWN_STABLE_SECONDS = 1.5
```

Thay vì:

``` text
UNKNOWN_STABLE_FRAMES = 12
```

để không phụ thuộc FPS.

### 5. Recognition Voting

Không nên kết luận chỉ từ một frame.

Ví dụ:

    Known
    Known
    Unknown
    Known
    Known
    ↓

    Known

Có thể dùng majority voting hoặc confidence accumulation.

### 6. Unknown Re-identification Cache

Nếu cùng một người lạ rời camera rồi quay lại trong vài chục giây thì
không nên tạo cảnh báo mới.

Có thể cache:

-   embedding
-   thời gian
-   event_id

để giảm spam.

## Pipeline đề xuất

``` text
Camera

↓

InsightFace Detect (1 lần)

↓

Tracker (ByteTrack)

↓

Track State

↓

Face Quality Filter

↓

Best Face Cache

↓

Embedding

↓

Qdrant Search

↓

Recognition Voting

↓

Identity State

↓

Unknown Stable

↓

Alert Manager

↓

Resolve Manager

↓

Redis / API / UI
```

## Track State đề xuất

``` python
class Track:
    track_id

    best_face
    best_embedding
    best_quality

    identity_status
    identity_label
    identity_score
    identity_confidence

    unknown_alert_sent
    unknown_alert_event_id

    last_seen_at
    last_recognition_at
```

## Kết luận

Pipeline hiện tại đã có kiến trúc rất tốt:

-   Một lần detect.
-   Hai luồng logic (Tracking và Recognition).
-   Không spam cảnh báo.
-   Có cơ chế resolve.

Các cải tiến nên ưu tiên:

1.  Thêm Face Quality.
2.  Lưu Best Face theo Track.
3.  Đổi sang ByteTrack nếu môi trường phức tạp.
4.  Unknown stable theo thời gian.
5.  Recognition voting.
6.  Unknown re-identification cache.

Sau các cải tiến này, pipeline hoàn toàn phù hợp để triển khai
production cho bài toán nhận diện khuôn mặt và phát hiện người lạ.
