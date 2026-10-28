# AquaWatch

Ứng dụng học thuật chạy local trên Windows: chọn hoặc tải video **trên mặt nước**, phân tích bằng YOLO đã fine-tune, xem box/cảnh báo theo thời gian, lưu ảnh bằng chứng và xuất nhật ký. Có chế độ **CCTV phát lại tuần tự** để AI phân tích từng phần trong khi video phát, cùng chế độ phân tích toàn bộ để xem lại. Toàn bộ mã, dữ liệu và kết quả nằm trong `D:\httm`; chưa kết nối camera vật lý.

**Trạng thái:** MVP kỹ thuật đã chạy qua API và đã fine-tune thật. Chất lượng tổng quát hóa còn thấp; chưa nghiệm thu như hệ thống cảnh báo đáng tin cậy. Xem [kết quả và giới hạn](docs/VALIDATION.md). Chưa kiểm tra UI/âm thanh/điện thoại trực tiếp: lượt kiểm tra mới nhất bị từ chối quyền điều khiển Chrome, với thông báo `Computer Use was not approved to use Google Chrome`. Xem [phạm vi QA giao diện](docs/UI_QA.md).

## Chạy trên máy hiện tại

Môi trường `.venv`, checkpoint fine-tune và video mẫu đã có. Mở PowerShell tại thư mục này:

```powershell
.\RUN.ps1
```

Mở **http://localhost:8000**. Dừng bằng Ctrl+C. Nếu PowerShell chặn script, có thể chạy trực tiếp mà không thay đổi execution policy:

```powershell
.\.venv\Scripts\python.exe -m uvicorn aquawatch.api:app --host 127.0.0.1 --port 8000
```

Máy đã xác minh: Python 3.12.10; RTX 2060 6 GB; RAM khoảng 15,8 GB; 12 CPU logic; PyTorch 2.7.1+cu126/CUDA hoạt động. Python 3.14 của hệ thống không được dùng cho môi trường này.

## Cài lại

Cần Windows 64-bit, Python 3.12, Internet cho lần cài/tải model. Mọi thư viện cài vào `.venv`:

```powershell
.\SETUP.ps1
# Nếu không có NVIDIA GPU:
.\SETUP.ps1 -CpuOnly
```

`requirements.txt` ghim thư viện ứng dụng; `requirements-lock.txt` ghi đầy đủ snapshot GPU của máy đã kiểm tra. Cài PyTorch theo `SETUP.ps1` trước khi dùng lock; bản `+cu126` cần index chính thức PyTorch. Không cần API key hoặc dịch vụ trả phí. Cài lại mặc định tải checkpoint cộng đồng; muốn tái tạo checkpoint fine-tune, làm theo [TRAINING.md](docs/TRAINING.md), không chỉ đổi tên model.

## Trình diễn

1. Chọn footage đã có trong thư viện hoặc tải video mới. Ưu tiên **MP4 H.264** để trình duyệt phát được. OpenCV đọc được AVI/MKV/MOV không bảo đảm trình duyệt phát được codec đó; chưa có chuyển mã tự động.
2. Xác nhận camera ghi từ trên mặt nước. Chọn fixed/PTZ và môi trường đúng thực tế. Giới hạn mỗi video 1 GB, 30 phút; một lượt phân tích tại một thời điểm.
3. Với đoạn camera ổn định, có thể vẽ polygon nước. Không có polygon thì không suy luận mất dấu. Khi góc nhìn đổi, polygon mất hiệu lực cho phần còn lại; cần tạo lượt mới trên đoạn ổn định.
4. Chọn chế độ. **CCTV · Giám sát theo dòng thời gian** mặc định đọc video tuần tự theo nhịp thời gian, trả kết quả từng phần và phát video khi đủ bộ đệm. Video tự chờ khi AI chưa xử lý tới đó; chỉ tua trong phần đã phân tích. Tạm dừng phần xem không dừng máy chủ phân tích/lưu phần tiếp theo. Nếu trình duyệt chặn phát tự động, nhấn **Phát giám sát**. **Phân tích toàn bộ để xem lại** xử lý xong toàn bộ trước khi xem kết quả.
5. Nhấn **Bật** âm thanh hoặc **Kiểm thử âm báo** theo nhu cầu. Âm báo không thay đổi âm lượng Windows. Rung/Notifications tùy thiết bị, quyền và secure context; chưa bảo đảm hỗ trợ điện thoại.
6. Box, mức cảnh báo và lịch sử giám sát chỉ dùng thời điểm đang xem; **Xem lại toàn bộ** được mở sau khi phiên dừng/hoàn tất. Nhấn sự kiện để xem thời điểm/ảnh bằng chứng; **Xác nhận đã xem** chỉ ghi nhận người dùng đã xem. JSON/CSV trên giao diện được mở khi hoàn tất. Hủy giữa chừng giữ phần đã phân tích và ghi rõ kết quả chưa đầy đủ.

Thư viện hiện có **13 clip đã sàng lọc, tổng 334,5 giây**, gồm bơi chủ động, cảnh nền không người, diễn tập chới với/hỗ trợ/nổi thụ động và bối cảnh cứu hộ thật. Có bộ lọc góc quay/tình huống, tìm kiếm tiếng Việt không dấu, thumbnail, nguồn và giấy phép. Phân biệt diễn tập với sự cố thật; nhãn tình huống không phải xác nhận y khoa. “Góc nhìn ổn định” chỉ mô tả hình ảnh quan sát được, không chứng minh camera đã lắp cố định. Các clip có xoay/zoom/cắt cảnh được ghi là kiểm thử phụ. Xem [nguồn, đoạn cắt và giới hạn thư viện](docs/VIDEO_LIBRARY.md).

Video USBP/DVIDS là footage cứu hộ thật quay từ bờ, có zoom/pan; dùng kiểm tra pipeline, **không phải benchmark CCTV tĩnh độc lập**. Mô hình vẫn có thể khoanh nhóm người, bỏ sót hoặc nhận diện sai. Không lấy số sự kiện dự đoán làm số tai nạn thật.

Để thử trong LAN: chủ động chạy `RUN.ps1 -Lan`, điện thoại cùng mạng mở `http://<IPv4-laptop>:8000`. Chưa có đăng nhập/TLS; chỉ dùng mạng tin cậy, không mở Internet. Firewall và HTTP LAN có thể hạn chế kết nối/Notifications. Chưa kiểm thử điện thoại thật trong phiên này.

## Huấn luyện và đánh giá

Đã fine-tune 8 epoch, ảnh 416, batch 4, seed 42 trên 192 ảnh duyệt thủ công: train121/val43/test28 theo ba cảnh. Chỉ dùng ảnh trên mặt nước trong tập fine-tune đã duyệt. Nguồn gốc training checkpoint ban đầu chưa rõ; nhãn nguồn yếu và quyền footage gốc chưa được xác minh đầy đủ. Không phát hành lại bộ ảnh như dữ liệu đã được bảo đảm quyền.

```powershell
.\.venv\Scripts\python.exe scripts\train_detector.py --dataset data\curated\deeprescue_v1 --model models\drowning_yolov8s.pt --epochs 8 --imgsz 416 --batch 4 --name ten_luot_moi --purpose experiment
.\.venv\Scripts\python.exe -m pytest -q -p no:cacheprovider
node --check web\app.js
node tests\frontend_timeline.test.cjs
```

Mỗi lượt train dùng tên mới; không ghi đè logs cũ. Run thực `data/training/finetune_v2/`; model được đưa vào `models/finetuned/weights/best.pt`, record tương ứng ở `data/training_record.json`. API chỉ chọn fine-tune nếu record hoàn tất và SHA-256 đúng. Lượt mới tự nạp model đã chọn; kết quả từng job ghi hash model dùng thật.

Các lệnh audit, so sánh baseline/candidate và khóa test nằm trong [TRAINING.md](docs/TRAINING.md). Đánh giá sự kiện có script `scripts/evaluate_events.py`, nhưng **chưa có ground truth video độc lập để báo precision/recall sự kiện, FP/giờ hoặc độ trễ cảnh báo**. Không thay bằng số giả.

## Tài liệu bàn giao

- [Giải pháp, so sánh công nghệ và kế hoạch](docs/SOLUTION_PLAN.md)
- [Khảo sát đủ bảy nguồn, nguồn bổ sung và sản phẩm thương mại](docs/DATA_RESEARCH.md)
- [Đối chiếu toàn bộ bốn bài giảng](docs/LECTURE_ALIGNMENT.md)
- [Kiến trúc, dữ liệu và thuật toán cảnh báo](docs/ARCHITECTURE.md)
- [Huấn luyện, kiểm duyệt và tái hiện](docs/TRAINING.md)
- [Kiểm thử, số đo thực và phần chưa đạt](docs/VALIDATION.md)
- [Thư viện video, nguồn và sàng lọc góc quay](docs/VIDEO_LIBRARY.md), [kiểm tra logic giao diện và giới hạn browser QA](docs/UI_QA.md)
- [Nguồn tài nguyên và giấy phép](docs/ASSETS.md), [danh mục giấy phép](LICENSES.md)

Hướng phát triển cần dữ liệu CCTV/video temporal có nguồn rõ, nhãn người duyệt và negative khó trước khi tinh chỉnh ngưỡng. Chưa có action/pose model, nhận diện cứu hộ, multi-camera, định vị nguy hiểm theo độ sâu hoặc gọi cứu hộ tự động. Đây là công cụ nghiên cứu, không thay nhân viên cứu hộ.
