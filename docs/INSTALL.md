# Cài đặt và chạy AquaWatch trên máy khác

Hướng dẫn này dành cho **Windows 64-bit và Python 3.12 64-bit**. Mỗi máy tạo môi trường `.venv` riêng; không chép `.venv` của máy khác. Các đường dẫn được tính từ thư mục dự án, không yêu cầu ổ `D:` hay tên thư mục `httm`.

AquaWatch phục vụ giao diện bằng FastAPI; không cần cài Node.js để chạy ứng dụng, không cần API key hoặc tài khoản cloud. Internet cần cho lần cài thư viện và lấy tài nguyên. Sau khi có đủ model và video, suy luận chạy tại máy chủ của bạn. Đây là phát lại video như luồng CCTV, chưa kết nối RTSP hoặc camera vật lý.

## 1. Chuẩn bị

- Cài Python **3.12 64-bit**, nên gồm Python Launcher (`py`). Kiểm tra trong PowerShell: `py -3.12 --version`. Nếu không có launcher, `SETUP.ps1` có thể dùng lệnh `python` trên PATH khi lệnh này thực sự trỏ đến Python 3.12 64-bit; kiểm tra bằng `python --version`.
- Có quyền ghi vào thư mục dự án và còn dung lượng để lưu môi trường Python, model, video tải lên và kết quả.
- Nếu dùng NVIDIA GPU, cài driver phù hợp và kiểm tra `nvidia-smi`. Script cài PyTorch có hỗ trợ CUDA; không cần tự cài CUDA Toolkit để chạy wheel PyTorch. Nếu máy không có NVIDIA GPU hoặc GPU không dùng được, chọn `-CpuOnly`.
- Git chỉ cần cho cách clone/cập nhật. Không bắt buộc nếu tải ZIP.

Môi trường tham chiếu đã từng chạy: Python 3.12.10, PyTorch 2.7.1, torchvision 0.22.1, CUDA wheel `cu126`, RTX 2060 6 GB. Đây là cấu hình đã kiểm tra, không phải cấu hình tối thiểu hay cam kết tốc độ cho máy khác. CPU có thể chậm hơn thời gian video; giao diện sẽ chờ phần AI đã xử lý thay vì hiển thị kết quả tương lai.

**Kiểm tra cài mới ngày 12/11/2026:** xuất đúng mã nguồn của bản phát hành sang thư mục khác, tạo `.venv` mới rồi chạy `SETUP.ps1 -CpuOnly` thành công; `pip check` không báo xung đột. Model fine-tune đã nạp trên CPU mà không có baseline, bộ 49 kiểm thử đạt. Tải mới archive Kaggle phiên bản 2 đúng checksum và dựng/giải mã đủ ba clip; API trả video byte-range và poster thành công.

Lượt phát lại clip #22 dài 30,03 giây trên CPU xử lý 151 khung mẫu trong khoảng 52,95 giây, tốc độ thực khoảng 2,85 khung mẫu/giây khi yêu cầu lấy mẫu 5 FPS. Có kết quả từng phần và hủy phiên giữ đúng phần đã xử lý. Đây là kiểm tra cài đặt/hiệu năng, không phải độ chính xác phát hiện; chưa kiểm tra tiếng ra loa hoặc điện thoại thật trong lượt này.

## 2. Lấy mã nguồn

### Cách A: Git

Trong PowerShell, chuyển tới thư mục muốn chứa dự án rồi chạy:

```powershell
git clone https://github.com/NTDung123/Aquawatch.git
Set-Location Aquawatch
```

### Cách B: ZIP

Mở repository, chọn **Code → Download ZIP**, giải nén toàn bộ, rồi mở PowerShell trong thư mục chứa `SETUP.ps1`, `RUN.ps1`, `requirements.txt` và `aquawatch/`. Không chạy lệnh từ thư mục ZIP chưa giải nén.

## 3. Cài thư viện và tài nguyên

Chạy một trong hai lệnh sau tại thư mục dự án:

```powershell
# Máy có NVIDIA GPU phù hợp
powershell -NoProfile -ExecutionPolicy Bypass -File .\SETUP.ps1

# Máy chỉ dùng CPU
powershell -NoProfile -ExecutionPolicy Bypass -File .\SETUP.ps1 -CpuOnly
```

`-ExecutionPolicy Bypass` ở đây chỉ áp dụng cho tiến trình PowerShell được mở bằng lệnh này; không thay đổi chính sách thực thi của toàn máy. Không cần mở PowerShell bằng quyền quản trị để cài vào thư mục cá nhân có quyền ghi.

Script tạo `.venv`, cài đúng phiên bản PyTorch rồi cài [requirements.txt](../requirements.txt), sau đó kiểm tra tài nguyên triển khai. Giữ cửa sổ mở cho tới khi script báo hoàn tất. Nếu một bước thất bại, xử lý thông báo lỗi rồi chạy lại cùng lệnh; không tiếp tục chạy ứng dụng với môi trường cài dở.

### Model và video không giống mã nguồn

Repository có checkpoint đã fine-tune `models/finetuned/weights/best.pt` và `data/training_record.json`. Clone/tải ZIP bản mới lấy được hai tệp này; không cần huấn luyện lại để mở ứng dụng. `SETUP.ps1` kiểm tra SHA-256 của checkpoint với training record. Model surface_v4 được công bố có SHA-256 `3651b252e2f96433c48311a1842a5772800d6d5954835ecdafe8e52d0a7b7871`.

Không chỉ đổi tên một model bất kỳ thành `best.pt`: record còn chứa ngưỡng và cách tiền xử lý mà ứng dụng cần dùng. Các dữ liệu huấn luyện, cache, upload và kết quả cá nhân không được coi là thành phần mã nguồn.

Video CCTV không được đóng gói chung với checkpoint. **Cài mặc định có model, thư viện video có thể rỗng.** Để tải và kích hoạt ba clip bể bơi đã được duyệt từ archive công khai, thêm `-SampleVideos` khi cài:

```powershell
# NVIDIA GPU
powershell -NoProfile -ExecutionPolicy Bypass -File .\SETUP.ps1 -SampleVideos

# CPU
powershell -NoProfile -ExecutionPolicy Bypass -File .\SETUP.ps1 -CpuOnly -SampleVideos
```

Nếu đã cài thư viện Python xong, chỉ cần chạy lệnh sau để bổ sung video, không cần cài lại PyTorch:

```powershell
.\.venv\Scripts\python.exe scripts\fetch_cctv_library.py --activate
```

Lệnh dùng review tại `assets/cctv_library_review.json`, kiểm tra archive đúng SHA-256, tạo MP4 H.264/poster và kích hoạt catalog. Nếu đã có catalog riêng, xem thông báo và bản sao lưu do script tạo; không cần tự sửa đường dẫn tuyệt đối. Tải video là bước tùy chọn, cần Internet và phụ thuộc nguồn bên ngoài còn cung cấp đúng archive đã duyệt. Nếu nguồn báo lỗi hoặc checksum thay đổi, không bỏ qua kiểm tra; vẫn có thể chạy ứng dụng với video của bạn.

Ba clip cùng nguồn/góc bể sóng, không được gọi là tập test độc lập. Archive do uploader khai báo MIT; quyền footage gốc chưa được xác minh riêng. Xem [nguồn và phạm vi sử dụng](VIDEO_LIBRARY.md). Thư viện phải có cả catalog lẫn các tệp clip/poster được catalog trỏ tới: chép riêng `data/video_library.json` không làm video xuất hiện nếu thiếu tệp, và thả MP4 vào thư mục `clips` không tự đưa chúng vào catalog đã duyệt.

Bạn luôn có thể chọn tệp CCTV bể bơi trên mặt nước bằng nút tải video trên web khi thư viện chưa có clip. Dùng tệp bạn có quyền sử dụng; không cần thư mục nguồn riêng của máy tác giả để chạy ứng dụng.

`SETUP.ps1 -Baseline`/`scripts/fetch_assets.py --baseline` là lựa chọn tải checkpoint cộng đồng để nghiên cứu, không thay thế bằng chứng tự fine-tune. Khi checkpoint fine-tune và record vẫn hợp lệ, ứng dụng tiếp tục ưu tiên model fine-tune. Không cần dùng tùy chọn này trong cài đặt thông thường. Video cứu hộ biển cũ cũng không được tải mặc định vào thư viện CCTV.

## 4. Khởi động và dừng

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File .\RUN.ps1
```

Mở **http://localhost:8000**. Giữ terminal đang chạy. Server nạp/làm nóng model khi khởi động, nên lần mở đầu có thể cần chờ trước khi AI sẵn sàng. Dừng server bằng **Ctrl+C** tại terminal đó.

Nếu cổng 8000 đang được ứng dụng khác dùng:

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File .\RUN.ps1 -Port 8001
```

Sau đó mở `http://localhost:8001`. Không cần đổi mã nguồn để đổi cổng.

Không cần activate `.venv`; script gọi đúng Python của dự án. Khi cần chạy trực tiếp để chẩn đoán lỗi:

```powershell
.\.venv\Scripts\python.exe -m uvicorn aquawatch.api:app --host 127.0.0.1 --port 8000
```

## 5. Kiểm tra sau khi cài

Trong PowerShell thứ hai, từ thư mục dự án:

```powershell
$status = Invoke-RestMethod http://localhost:8000/api/status
$status.model | Format-List
$status.hardware | Format-List
```

Các trường cần xem:

| Trường | Ý nghĩa |
|---|---|
| `ready` và `loaded` | Cùng là `True` khi model đã nạp thành công |
| `error` | Bình thường không có thông báo lỗi |
| `fine_tuned` | `True` khi thực sự dùng checkpoint fine-tune kèm record hợp lệ |
| `path`, `name` | Model server đang dùng; dùng để phát hiện tải nhầm bản baseline |
| `device`, `hardware.cuda` | Cho biết đang chạy CPU hay NVIDIA GPU |
| `preprocessing` | Với model surface_v4 đã công bố là `stretch640` |

Sau đó kiểm tra trực tiếp trên web:

1. Chọn một video thư viện hoặc tải một tệp CCTV bể bơi trên mặt nước. Video và nhận diện theo thời gian phải tự bắt đầu; không cần bấm phân tích lần thứ hai.
2. Kiểm tra trạng thái AI và khung nhận diện thay đổi theo thời điểm đang xem. Khi AI chưa xử lý kịp, video chờ kết quả là hành vi dự kiến.
3. Nhấn **Kiểm thử âm báo** và nghe bằng loa/tai nghe đang dùng. Ứng dụng chuẩn bị âm báo ngay trong thao tác chọn/phát video. Nếu trình duyệt vẫn chặn, nhấn **Bật âm báo**; kiểm tra thanh trạng thái âm báo, âm lượng ứng dụng, trạng thái mute tab và âm lượng Windows. Video nguồn mặc định tắt tiếng không có nghĩa âm báo AI bị tắt.
4. Tạm dừng/phát lại và đổi clip để kiểm tra thao tác bình thường. Cảnh báo nằm ngoài khung video; khung màu trên đối tượng là lớp hiển thị nhận diện.
5. Khi có sự kiện, thử mở bằng chứng và xác nhận đã xem. Xác nhận chỉ ghi nhận thao tác của người vận hành, không kết luận tình huống đã an toàn.

Chỉ số model được công bố trong README là đánh giá trên dữ liệu của dự án, không thay thế kiểm tra trên video/camera của máy nhận. Ứng dụng học thuật chưa được kiểm định thay nhân viên cứu hộ.

## 6. Cho điện thoại/máy khác trong LAN truy cập

Chạy trên máy có model:

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File .\RUN.ps1 -Lan
ipconfig
```

Máy cùng mạng mở `http://<IPv4-của-máy-chủ>:8000`, ví dụ `http://192.168.1.20:8000`. Điện thoại chỉ mở trình duyệt; việc suy luận vẫn chạy trên máy chủ. `localhost` trên điện thoại là chính điện thoại, không trỏ về laptop.

Nếu không truy cập được, kiểm tra hai thiết bị cùng mạng, IP/cổng đúng, mạng khách không cô lập thiết bị, và Windows Firewall cho phép Python/cổng đã chọn trên **mạng riêng** theo chính sách của bạn. Không tự mở router ra Internet. Ứng dụng hiện chưa có đăng nhập hoặc TLS; chỉ sử dụng trong mạng tin cậy. Notifications/rung có thể bị giới hạn trên HTTP LAN; âm báo vẫn cần thao tác người dùng và quyền của trình duyệt. Chưa có bằng chứng kiểm thử mọi trình duyệt/điện thoại.

## 7. Cập nhật và chuyển máy

Nếu cài bằng Git, dừng server rồi cập nhật:

```powershell
git status --short
git pull --ff-only
powershell -NoProfile -ExecutionPolicy Bypass -File .\SETUP.ps1
powershell -NoProfile -ExecutionPolicy Bypass -File .\RUN.ps1
```

Nếu `git status` có các thay đổi mã nguồn bạn cần giữ, commit hoặc sao lưu chúng trước khi pull. Nếu Git báo nhánh đã phân kỳ, dừng để giải quyết thay vì dùng lệnh reset/xóa toàn bộ. Với bản ZIP, giải nén bản mới vào thư mục mới và chạy lại setup.

Nhấn **Ctrl+F5** trên trình duyệt sau khi cập nhật để lấy JavaScript/CSS mới. Việc cập nhật mã nguồn không tự chuyển upload/lịch sử của máy tác giả sang máy nhận.

Muốn giữ kết quả cá nhân, dừng server trước khi sao lưu cả thư mục `data` và phần model triển khai tương ứng. SQLite chứa đường dẫn video upload; việc chép nguyên dữ liệu cũ sang ổ/thư mục khác có thể cần chuyển đổi đường dẫn, vì vậy cách đơn giản để chuyển máy là cài bản mới, lấy lại tài nguyên triển khai và tải lại các video cần dùng. Không chép `.venv`, `.work` hoặc cache để thay cho cài đặt.

## 8. Xử lý lỗi thường gặp

| Hiện tượng | Cách kiểm tra/xử lý |
|---|---|
| `py` không tồn tại hoặc không tìm thấy Python 3.12 | Cài Python 3.12 64-bit kèm launcher, mở lại PowerShell, kiểm tra `py -3.12 --version`; hoặc bảo đảm `python` trên PATH đúng bản 3.12 64-bit |
| PowerShell báo không được chạy script | Dùng đúng lệnh `powershell -NoProfile -ExecutionPolicy Bypass -File ...` ở trên; không cần đổi policy toàn hệ thống |
| Pip tải lỗi, timeout hoặc không có phiên bản tương thích | Kiểm tra mạng/proxy và Python 3.12; giữ nguyên lỗi để chẩn đoán, không tự thay toàn bộ dependency sang bản mới |
| CUDA/driver lỗi hoặc `hardware.cuda=False` | Kiểm tra `nvidia-smi`; nếu chỉ cần chạy demo, cài lại bằng `SETUP.ps1 -CpuOnly`; chạy CPU có thể chậm |
| `ready=False`, model thiếu hoặc checksum sai | Xem `model.error`, kiểm tra model và training record theo hướng dẫn tài nguyên; không tắt kiểm tra SHA-256 để ép nạp tệp |
| Server chạy nhưng thư viện rỗng | Đây là trạng thái bình thường nếu chưa dùng `-SampleVideos`. Chạy `scripts/fetch_cctv_library.py --activate` bằng Python `.venv` hoặc dùng nút tải tệp. Không cần thư mục nguồn trên máy tác giả |
| Video không phát hoặc chỉ có màn hình đen | Ưu tiên MP4 H.264; OpenCV đọc được AVI/MKV/MOV không bảo đảm browser hỗ trợ codec. Thử phát bằng nút trên video nếu autoplay bị chặn |
| Có cảnh báo hình ảnh nhưng chưa nghe âm | Dùng **Kiểm thử âm báo**, **Bật âm báo**, tăng âm lượng ứng dụng, bỏ mute tab, kiểm tra loa/Windows; trình duyệt có thể tạm dừng âm khi chưa có thao tác cho phép |
| Video liên tục chờ AI | Xem thiết bị CPU/GPU, đóng tác vụ nặng, dùng video nhẹ hơn. Hệ thống chỉ chạy một job inference đồng thời; chờ buffer không phải bằng chứng video đã an toàn |
| Upload bị từ chối | Mỗi tệp tối đa 1 GB và 30 phút; dùng CCTV bể bơi trên mặt nước và định dạng API hỗ trợ. Không dùng footage camera dưới nước |
| Cổng đã được sử dụng | Dùng `RUN.ps1 -Port 8001` và mở đúng URL, hoặc dừng phiên server cũ của chính bạn bằng Ctrl+C |

## 9. Kiểm tra mã nguồn và huấn luyện thêm

Các bước này dành cho người phát triển, không bắt buộc để mở web. Node.js chỉ cần cho hai lệnh kiểm tra JavaScript cuối:

```powershell
.\.venv\Scripts\python.exe -m pytest -q -p no:cacheprovider
node --check web\app.js
node tests\frontend_timeline.test.cjs
```

Muốn tự huấn luyện/fine-tune, xem [TRAINING.md](TRAINING.md), [kiểm duyệt dữ liệu](EXPANDED_DATASET.md) và [giới hạn đánh giá](VALIDATION.md). Dữ liệu train không tự được đưa vào bản clone chỉ vì mã huấn luyện có trong repo; không trộn các clip demo cùng nguồn/camera vào test độc lập.
