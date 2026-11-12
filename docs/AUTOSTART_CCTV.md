# Chọn video là tự nhận diện CCTV

Cập nhật **29/10/2026, giờ Việt Nam**. Thay đổi này hoàn tất luồng chọn/tải video tự chạy, thư viện CCTV bể bơi mới và triển khai checkpoint đã fine-tune mở rộng.

## Luồng sử dụng hiện tại

Chọn một thẻ video, chọn trong dropdown hoặc tải tệp CCTV bể bơi lên. Giao diện tự tạo phiên `realtime`, camera cố định, môi trường pool, lấy mẫu5FPS và dùng ngưỡng đã hiệu chỉnh0,35. Không còn bước xác nhận checkbox hoặc bấm nút bắt đầu trong luồng chính. Tùy chọn phân tích lại/batch nằm trong phần nâng cao.

Video được phát im lặng để trình duyệt cho phép autoplay; âm cảnh báo riêng tự được chuẩn bị trong thao tác chọn/phát. Nếu trình duyệt chặn, thanh trạng thái hiện nút **Bật âm báo**; lựa chọn tắt âm của người dùng được lưu. Banner nằm dưới khung video. Đổi video tự hủy và chờ phiên cũ dừng, rồi khởi động clip mới. Chuỗi lựa chọn nhanh chỉ chạy lựa chọn cuối; phản hồi upload/job cũ không được gắn vào video mới. Mở lịch sử chỉ phục hồi kết quả, không tự tạo lượt phân tích mới.

Model được nạp trước khi máy chủ báo sẵn sàng. Lượt đo startup trên máy này: **9,751 giây**, diễn ra một lần khi khởi động. Khi chọn video sau đó, model giữ trong bộ nhớ; UI vẫn hiển thị trạng thái chờ thật nếu máy chủ chưa sẵn sàng hoặc mất kết nối. Không hứa mọi máy có độ trễ bằng nhau.

## Thư viện đang hiển thị

Active manifest `data/video_library.json` chỉ còn **3 clip, tổng87,7 giây**:

| Clip | Thời lượng | Nội dung quan sát |
|---|---:|---|
| CCTV bể sóng · cứu hộ #22 | 30,03giây | Người gặp khó khăn trên mặt nước và nhân viên tiếp cận/hỗ trợ |
| CCTV bể sóng · cứu hộ #19 | 29,23giây | Góc quan sát trên cao liên tục, tình huống nguy cơ và hỗ trợ |
| CCTV bể sóng · cứu hộ #13 | 28,43giây | Tình huống cầu cứu/cứu hộ trong bể, camera trên mặt nước |

Đã kiểm tra timeline mỗi giây và biên đoạn; không thấy cảnh dưới nước, cắt cảnh hoặc marker chỉ sẵn mục tiêu trong các clip giữ. Kiểm tra giải mã toàn bộ3/3 clip đạt. Giữ nguyên toàn clip archive, không cắt theo kết quả AI. Vị trí lắp phần cứng chưa có hồ sơ độc lập; “CCTV” ở đây chỉ các đoạn quan sát từ trên cao với góc nhìn cố định đã kiểm trực tiếp.

Nguồn: dataset Kaggle `nvbangg/drowning-test`, nguồn gốc series *Wavepool Lifeguard Rescue* của kênh *Lifeguard Rescue*. MIT là khai báo của người đăng dataset; quyền footage gốc chưa được xác minh riêng. Dùng làm tham chiếu học thuật local, không tuyên bố được phép phân phối lại không giới hạn. Các clip cùng bể/camera và có thể trùng nguồn ảnh train, vì vậy không phải ba bài test độc lập với training.

Danh mục cũ50 entry được lưu nguyên byte trong `data/library/history/video_library_pre_cctv_b01a0a5cfe8b.json`; các tệp video và kết quả lịch sử cũ được giữ. Chúng không còn xuất hiện trong thư viện chính. Xem `data/cctv_library_audit.json`, `cctv_library_review.json`, `docs/PROVIDED_CCTV_AUDIT.md` và script `scripts/fetch_cctv_library.py`.

## Số đo chạy thật

`data/evaluation/cctv_autostart_realtime_20261029.json` ghi nhận HTTP thật, checkpoint v4 thật và clip #22 thật:

- Phần kết quả khung hình đầu tiên được quan sát sau **0,422giây từ lúc gửi yêu cầu**, khi model đã nóng. Đây không phải độ trễ phát hiện từ lúc nạn nhân bắt đầu gặp nguy hiểm và không phải phép đo click trên Chrome.
- Clip30,03giây được xử lý tuần tự trong30,21giây;151 samples, nhịp hiệu dụng5FPS;492 detections dự đoán;4 đoạn trạng thái, mức tối đa3.
- Có kết quả từng phần trong lúc job chạy. Assertion xác minh timestamp sample/event không vượt `processed_until` và thời gian nguồn.
- Hủy một lượt khác giữ đúng prefix đã xử lý đến1,0giây, `partial=true`, không báo hoàn tất giả.

Chạy batch để đối chiếu output trên cả3 clip, cùng model/ngưỡng đã chọn bằng validation, lưu `data/evaluation/cctv_v4_library_20261029.json`:

| Clip | Samples | Detections dự đoán | Đoạn cảnh báo mức≥2 | Thời điểm cảnh báo đầu |
|---|---:|---:|---:|---:|
| #13 |143|446|1|15,0giây|
| #19 |147|429|7|2,2giây|
| #22 |151|492|2|13,0giây|

Đây là đầu ra dự đoán, **không chứng minh mọi box/cảnh báo đều đúng nạn nhân**. Clip #19 có cảnh báo rất sớm so với mốc khó khăn ước lượng bằng mắt; cần gán nhãn theo người/thời gian trước khi tính false alarm hoặc recall sự kiện. Đã xem ảnh bằng chứng một số cảnh báo #22 để kiểm tra box thật, không dùng ảnh này để chứng nhận độ chính xác. Ba clip đều có cảnh báo không đồng nghĩa recall100%.

Model triển khai: `surface_v4_continue30_threads`, SHA `3651b252e2f96433c48311a1842a5772800d6d5954835ecdafe8e52d0a7b7871`, ngưỡng0,35, tiền xử lý `stretch640`. Train thêm30 epoch trên bộ1.313 ảnh đã duyệt; val/test giữ tách cảnh. Test169 ảnh có mAP50 tổng45,81% và AP50 lớp nguy cơ58,62%; đó là metrics ảnh theo nhãn nguồn yếu, chưa phải chất lượng cảnh báo CCTV đã được kiểm định.

## Kiểm thử giao diện và giới hạn

- Python regression ngày 12/11: **49 passed**, một cảnh báo deprecation Starlette/httpx; bổ sung kiểm tra đường dẫn chuyển máy và fine-tune không cần baseline.
- `node --check web/app.js` và `node tests/frontend_timeline.test.cjs`: đạt, 80 liên kết HTML; kiểm thử bất đồng bộ chọn/upload tự chạy, đổi clip, phản hồi cũ, phiên lịch sử, chờ model và khôi phục âm báo.
- GET HTML/JS và active catalog qua HTTP: thành công; thư viện chính đúng3 clip mới. Video byte-range206 hỗ trợ phát/tua.
- Chrome đang mở trang AquaWatch nhưng công cụ Computer Use tiếp tục từ chối: `Computer Use was not approved to use Google Chrome`. Vì vậy chưa có xác nhận trực quan trên Chrome/điện thoại hoặc phép thử nghe loa; các kiểm tra Node/HTTP không thay thế bước đó. Xem `UI_QA.md`.

Model vẫn có thể nhận diện nhầm/bỏ sót. Chưa có kết nối camera vật lý hoặc mạng action recognition riêng; detector ảnh kết hợp tracking và logic thời gian để phát lại footage như một luồng CCTV.
