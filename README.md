# AquaWatch

Ứng dụng học thuật nhận diện **dấu hiệu nguy cơ đuối nước trong video CCTV bể bơi quay từ trên mặt nước**. Chọn hoặc tải video để tự phát và phân tích tuần tự theo thời gian; giao diện hiển thị đối tượng, mức cảnh báo, âm báo, ảnh bằng chứng và nhật ký JSON/CSV. Backend FastAPI và model YOLO chạy trên máy của bạn.

**[Hướng dẫn cài đặt trên máy khác →](docs/INSTALL.md)** · [Nguồn video](docs/VIDEO_LIBRARY.md) · [Huấn luyện](docs/TRAINING.md) · [Kiểm thử giao diện](docs/UI_QA.md)

## Cài và chạy

Yêu cầu: **Windows 10/11 64-bit, Python 3.12 64-bit**, Internet khi cài thư viện; Git hoặc tải ZIP từ GitHub. NVIDIA GPU là tùy chọn, CPU cũng chạy được nhưng có thể xử lý chậm hơn tốc độ video.

Mở PowerShell trong thư mục muốn lưu dự án:

```powershell
git clone https://github.com/NTDung123/Aquawatch.git
cd Aquawatch
powershell -ExecutionPolicy Bypass -File .\SETUP.ps1 -SampleVideos
powershell -ExecutionPolicy Bypass -File .\RUN.ps1
```

Mở **http://localhost:8000**. Dừng máy chủ bằng **Ctrl+C**. `ExecutionPolicy Bypass` trong lệnh trên chỉ áp dụng cho tiến trình PowerShell đó.

Máy không có NVIDIA hoặc cần dùng CPU:

```powershell
powershell -ExecutionPolicy Bypass -File .\SETUP.ps1 -CpuOnly -SampleVideos
```

- Setup tạo `.venv`, cài PyTorch 2.7.1/torchvision 0.22.1 cùng thư viện đã ghim, rồi kiểm tra checksum model. Máy có NVIDIA được chọn wheel CUDA 12.6; có thể chọn CPU rõ ràng bằng `-CpuOnly`.
- **Checkpoint đã fine-tune và record đi kèm trong repo**: không cần huấn luyện lại để trình diễn. Setup mặc định kiểm tra model này; `-Baseline` chỉ tải thêm checkpoint cộng đồng để tham khảo. Ứng dụng ưu tiên checkpoint fine-tune hợp lệ.
- `-SampleVideos` tải và dựng **3 clip CCTV đã duyệt, tổng 87,7 giây** từ nguồn gốc đã ghim. Bỏ tùy chọn này nếu chỉ dùng video của bạn; thư viện trên bản clone mới sẽ trống cho tới khi thêm video.
- Thư mục dự án có thể đặt ở đường dẫn bất kỳ có quyền ghi. Không cần thư mục `D:\httm` hoặc `D:\drowning-detection` trên máy nhận.

Xem [INSTALL.md](docs/INSTALL.md) cho cách tải ZIP, khắc phục lỗi Python/CUDA/codec, kiểm tra model, chạy LAN và cập nhật phiên bản. `requirements-lock.txt` là snapshot GPU của máy phát triển; dùng `SETUP.ps1` để chọn đúng PyTorch CPU/GPU trên máy mới.

## Sử dụng

1. Chọn một clip trong thư viện hoặc tải tệp CCTV. Video và AI tự chạy; các thông số mặc định là camera cố định, bể bơi và ngưỡng của model đang triển khai. Nếu trình duyệt chặn phát, nhấn **Phát giám sát**.
2. Máy chủ nạp model một lần rồi giữ trong bộ nhớ. Giao diện chờ nếu AI chưa xử lý tới thời điểm đang xem; chỉ tua trong phần đã phân tích. Có thể đổi video khi đang chạy: phiên trước được hủy trước khi phiên mới bắt đầu.
3. Âm báo được chuẩn bị ngay trong thao tác chọn/phát video. Thanh trạng thái âm cho biết đã sẵn sàng, bị trình duyệt chặn hoặc do bạn tắt. Nhấn **Bật âm báo** để cho phép và báo lại sự kiện đang diễn ra; dùng **Kiểm thử âm báo** để kiểm tra loa. Lựa chọn tắt âm được giữ khi đổi video và tải lại trang.
4. Banner cảnh báo nằm **dưới khung video**; box nhận diện vẫn bám đối tượng. Âm báo chỉ dùng sự kiện tại thời điểm đang phát, có giới hạn nhắc lại và dừng khi tạm dừng video.
5. Nhấn sự kiện để xem thời điểm/ảnh bằng chứng. **Xác nhận đã xem** ghi nhận thao tác của người dùng. Mở phiên đã lưu chỉ phục hồi kết quả; hủy giữa chừng giữ phần đã xử lý.
6. Mở **Tùy chọn nâng cao / phân tích lại** khi cần thay ngưỡng, chế độ xử lý hoặc vùng nước. Nguồn video mặc định tắt tiếng; âm báo AI là kênh riêng.

Ưu tiên **MP4 H.264**, tối đa **1 GB / 30 phút mỗi tệp**, một phiên inference tại một thời điểm. OpenCV đọc được tệp không bảo đảm trình duyệt hỗ trợ codec của tệp đó. Không dùng footage camera chìm dưới nước. Đây là phát lại video có sẵn theo thời gian, chưa kết nối camera vật lý.

## Model và dữ liệu

Model triển khai: **YOLOv8s · surface_v4_continue30_threads** tại `models/finetuned/weights/best.pt`, khoảng 22,5 MB. Record: [data/training_record.json](data/training_record.json). SHA-256:

```text
3651b252e2f96433c48311a1842a5772800d6d5954835ecdafe8e52d0a7b7871
```

V3 khởi tạo từ COCO đã train 49 epoch; V4 tiếp tục từ BEST của V3 thêm 30 epoch. Bộ ảnh đã duyệt gồm **1.313 ảnh: 1.007 train / 137 validation / 169 test**, từ Alanoud và Mibugi, chia theo nhóm cảnh. Model dùng ngưỡng **0,35** và tiền xử lý `stretch640`.

- Test ảnh: **mAP50 tổng 45,81%; AP50 lớp nguy cơ 58,62%; mAP50–95 tổng 14,00%**.
- Trên validation, lớp nguy cơ có precision 65,15% / recall 71,67% tại IoU 0,5; chưa đạt mục tiêu recall 80%.
- Các số đo trên dùng nhãn ảnh nguồn; chưa chứng minh độ chính xác cảnh báo sự kiện video. Clip demo có thể trùng bể/camera với ảnh train.

Dữ liệu train, video gốc, môi trường Python, database và kết quả cá nhân nằm ngoài Git. Repo chứa mã xử lý, cấu hình duyệt 3 clip và checkpoint cần để chạy inference. Thư mục 75 video nguồn trên máy phát triển **chưa được duyệt/nhập đầy đủ**; không coi đó là 75 video sẵn có trong bản phát hành. Xem [audit nguồn cục bộ](docs/PROVIDED_CCTV_AUDIT.md).

Nguồn và điều kiện sử dụng thành phần được ghi trong [LICENSES.md](LICENSES.md). Model là sản phẩm học thuật hỗ trợ nghiên cứu, chưa được kiểm định để thay nhân viên cứu hộ.

## Kiểm tra và phát triển

Sau khi cài môi trường:

```powershell
.\.venv\Scripts\python.exe -m pytest -q -p no:cacheprovider
node --check web\app.js
node tests\frontend_timeline.test.cjs
.\.venv\Scripts\python.exe scripts\fetch_assets.py
```

Node.js chỉ cần cho kiểm thử JavaScript, không cần để chạy ứng dụng. Kiểm thử logic gồm tự chạy/đổi video, kết quả theo thời gian, âm báo bị chặn rồi bật lại, giữ tắt âm và banner ngoài khung hình. Kiểm thử tự động chưa xác nhận âm phát ra loa hay bố cục trên điện thoại thật.

Các lệnh tải/tạo lại thư viện và kiểm tra HTTP nằm trong [tài liệu thư viện](docs/VIDEO_LIBRARY.md); quy trình tạo dataset, fine-tune và đánh giá nằm trong [TRAINING.md](docs/TRAINING.md). Dataset/run đầy đủ phải chuẩn bị riêng khi muốn tái huấn luyện. Đường dẫn máy huấn luyện trong record là thông tin lịch sử, không phải điều kiện chạy inference.

## Tài liệu

- [Cài trên máy khác, cập nhật và xử lý lỗi](docs/INSTALL.md)
- [Kiến trúc và thuật toán cảnh báo](docs/ARCHITECTURE.md)
- [Dataset và giới hạn nguồn](docs/EXPANDED_DATASET.md)
- [Tự chạy CCTV và số đo API](docs/AUTOSTART_CCTV.md)
- [Thư viện video và nguồn gốc](docs/VIDEO_LIBRARY.md)
- [QA giao diện/âm báo](docs/UI_QA.md), [đánh giá và giới hạn](docs/VALIDATION.md)
- [Đối chiếu bài giảng](docs/LECTURE_ALIGNMENT.md), [kế hoạch giải pháp](docs/SOLUTION_PLAN.md)
