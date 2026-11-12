# Thư viện CCTV bể bơi hiện tại

Cập nhật **29/10/2026**. Thư viện chính đã thay toàn bộ danh mục cũ bằng **3 clip quan sát bể sóng có tình huống nguy cơ và cứu hộ**, tổng **87,7 giây**. Chọn một clip trên web là tự phát và nhận diện theo thời gian.

| Clip | Độ dài | Nguồn gốc |
|---|---:|---|
| CCTV bể sóng · tình huống cứu hộ #22 |30,03 giây|[Lifeguard Rescue22](https://www.youtube.com/watch?v=IOHBGgt5oG4)|
| CCTV bể sóng · tình huống cứu hộ #19 |29,23 giây|[Lifeguard Rescue19](https://www.youtube.com/watch?v=T5mDQeDkca0)|
| CCTV bể sóng · tình huống cứu hộ #13 |28,43 giây|[Lifeguard Rescue13](https://www.youtube.com/watch?v=vt6ZBq5jVec)|

Các tệp được lấy từ **phiên bản 2** của archive công khai [Kaggle nvbangg/drowning-test](https://www.kaggle.com/datasets/nvbangg/drowning-test/versions/2), không tải trực tiếp bản dài từ YouTube. Script ghim `datasetVersionNumber=2` và SHA-256 vì phiên bản mới nhất đã thay nội dung. Giữ toàn bộ clip trong archive; offset so với YouTube gốc chưa biết. MP4 H.264 không âm nguồn, tên tiếng Việt UTF-8 đã kiểm tra. Timeline mỗi giây và biên đoạn đã được xem; không thấy underwater, cắt cảnh hoặc vòng/mũi tên chỉ sẵn mục tiêu trong phần giữ. Full-decode3/3 đạt.

**Nguồn và giới hạn quyền:** MIT là giấy phép do người đăng dataset khai báo. Kênh gốc là Lifeguard Rescue; quyền footage gốc chưa được xác minh riêng. Đây là tham chiếu học thuật local, không khẳng định được phép phân phối lại không giới hạn. Ba clip cùng bể/góc quan sát, có khả năng trùng imagery với ảnh train; không dùng làm bằng chứng test video độc lập. Review xác nhận framing ổn định trên cao, không có hồ sơ độc lập về phần cứng lắp camera.

- Active catalog: `data/video_library.json`; bản được kiểm tra trước kích hoạt: `data/cctv_video_library.json`.
- Cấu hình duyệt được kèm repo: `assets/cctv_library_review.json`. Decode/audit sinh cục bộ trong `data/`.
- Máy mới: `powershell -ExecutionPolicy Bypass -File .\SETUP.ps1 -SampleVideos` hoặc sau khi cài môi trường, `.\.venv\Scripts\python.exe scripts\fetch_cctv_library.py --activate`. Script tải archive đã ghim, kiểm tra hash, dựng H.264/poster, full-decode rồi kích hoạt catalog; catalog trước được sao lưu trong `data/library/history/`.
- Chạy `fetch_cctv_library.py` không có `--activate` chỉ tạo catalog nháp. Nếu nguồn tải đổi hash, script dừng để kiểm tra lại nguồn; có thể tải video của bạn qua web khi nguồn công khai không còn truy cập được.
- Kiểm tra toàn bộ clip/poster qua máy chủ đang chạy: `.\.venv\Scripts\python.exe scripts\verify_library_api.py`.
- Lịch sử50 video: `data/library/history/video_library_pre_cctv_b01a0a5cfe8b.json`. Giữ video gốc và kết quả cũ để truy vết; không còn hiển thị trong thư viện chính.
- [Audit nguồn/video](PROVIDED_CCTV_AUDIT.md), [luồng tự chạy và số đo thật](AUTOSTART_CCTV.md), [tài liệu thư viện cũ](history/VIDEO_LIBRARY_before_20261029.md).
