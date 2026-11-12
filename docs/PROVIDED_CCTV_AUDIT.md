# Kiểm tra video từ các nguồn người dùng đã cung cấp

Ghi chú đồng bộ repo **12/11/2026**: catalog đang hoạt động vẫn là ba clip bên dưới. Thư mục nguồn cục bộ gồm 75 tệp, khoảng 5,79 GB; file duyệt mở rộng còn ở trạng thái `review_in_progress`, chưa có đoạn được phê duyệt để import. Các tệp đó không được tính thành thư viện đã hoàn tất và không nằm trong Git. Máy khác dùng cấu hình duyệt ba clip tại `assets/cctv_library_review.json` hoặc tải CCTV riêng qua giao diện.

Ngày review: 29/10/2026. Phạm vi mới là **cảnh bể bơi nhìn từ camera trên cao cố định, có tình huống nguy cơ và hỗ trợ cứu hộ**. Không chọn beach, camera dưới nước/half-water hoặc bài diễn tập cầm máy chỉ để tăng thư viện.

## Ba clip nvbangg đạt điều kiện góc nhìn

Đã giải nén ba file từ `data/research/nvbangg.zip`, xem **toàn bộ timeline từng giây**, rồi xem thêm các mốc 0,5 giây quanh tuột phao/người cứu hộ tiếp cận. Các bản được giữ nằm tại `data/library/research_cctv/nvbangg/`. Không thêm chữ, circle/arrow hoặc box gợi ý trước mục tiêu. Không dùng dự đoán AI để chọn mốc hoặc cắt video.

| Archive clip | Thời lượng | Quan sát nguy cơ, thời gian trong clip | Người cứu hộ tiếp cận/hỗ trợ |
| --- | ---: | --- | --- |
| `IOHBGgt5oG4.mp4` · Wavepool Lifeguard Rescue22 | 30,03 giây | Người mặc đồ hồng ở foreground tuột phao khoảng **6 ±1 giây**, lặp lại động tác tay và chìm/ngoi | Người cứu hộ vào nước khoảng 18,5 giây, tiếp xúc khoảng **21 ±1 giây**, hỗ trợ đến cuối clip |
| `T5mDQeDkca0.mp4` · Rescue19 | 29,2292 giây | Người cạnh dây phân cách liên tục quạt tay/nhấp nhô; mốc rõ hơn khoảng **6 ±2 giây**. Những giây đầu có thể đã có khó khăn, không gán là bình thường chắc chắn | Vào nước khoảng 12 giây, tiếp xúc khoảng **16 ±1 giây**, hỗ trợ đến cuối clip |
| `vt6ZBq5jVec.mp4` · Rescue13 | 28,4284 giây | Người ở upper-center/right mất phao khoảng **9 ±1 giây**, sau đó lặp lại động tác tay/chìm ngoi | Vào nước khoảng 24,5 giây, tiếp xúc khoảng **26,5 ±1 giây**, hỗ trợ đến cuối clip |

Đây là **mốc hành vi quan sát được**, không phải thời điểm khởi phát hay kết thúc đuối nước được xác nhận y khoa. Các clip có nhiều người bơi bình thường bên cạnh; không coi mọi người trong một video cứu hộ là target nguy cơ.

Camera giữ góc trên mặt nước ổn định trong toàn bộ ba clip, phù hợp góc quan sát surveillance. Không thấy scene cut, shot underwater, marker chỉ sẵn nạn nhân hoặc montage. **Chưa xác minh được cấu tạo/vị trí gắn camera vật lý**, vì vậy bằng chứng trực tiếp là góc quay ổn định trên cao, không phải chứng nhận thiết bị CCTV.

Giữ **toàn bộ mỗi archive clip** để có trước/sau tình huống hỗ trợ. Bản Kaggle dài khoảng 28–30 giây, khác thời lượng video YouTube gốc; `original_youtube_offset=null`. Không ánh xạ nhầm giây thứ 6 của archive thành giây thứ 6 trên YouTube.

Research agent đã kiểm tra YouTube oEmbed/videoDetails, xác nhận cả ba nguồn thuộc kênh **Lifeguard Rescue** và title tương ứng. Metadata/source URL được lưu cùng thư viện. Kaggle uploader khai báo **MIT**, nhưng quyền footage YouTube gốc **chưa được xác minh độc lập**; không dùng MIT của uploader để khẳng định quyền tác giả gốc đã rõ.

Ba clip cùng waterpark/wavepool, có thể trùng cảnh hoặc frame trong dữ liệu train. Chúng được dùng làm thư viện minh họa địa phương; **không gọi là ba camera/sự kiện test độc lập chưa từng thấy**.

Bằng chứng:

- `data/library/research_cctv/nvbangg_review.json`: đường dẫn file, SHA-256, FPS/frame/duration, nguồn và các mốc thủ công.
- `data/library/research_cctv/review/<video-id>/page_000.jpg`, `page_001.jpg`, `refined.jpg`: toàn bộ timeline 1 giây và các mốc được xem kỹ.
- `data/library/research_cctv/nvbangg_decode_audit.json`: kiểm decode tuần tự và sàng lọc scene cut theo từng frame.

## Kho randhana

Research reviewer đã kiểm tra 12 MP4 trong `randhana_repo.zip`; tất cả thuộc góc underwater hoặc half-water, **0 clip đạt phạm vi mới**. Không đưa chúng vào danh sách được chọn ở trên. Inventory là `data/library/randhana_video_inventory.json`, các bản nguồn nằm trong `data/library/raw/randhana_pinned/`, contact sheet ở `data/library/review/cctv_candidates/`.

MIT ở repository áp dụng theo tuyên bố của kho, không tự xác lập nguồn gốc/quyền riêng của mỗi footage. Nhóm dữ liệu chỉ bàn giao ba clip đạt góc nhìn; agent chính quản lý thay active catalog và kiểm thử phát video/tự chạy nhận diện.
