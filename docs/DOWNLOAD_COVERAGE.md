# Phạm vi dữ liệu đã tải và các nguồn bị loại/chưa tải

Kiểm tra ngày **28/10/2026**. “Đã tải đầy đủ archive” có nghĩa file ZIP thực đã nằm trong dự án và có checksum; **không có nghĩa mọi ảnh/video trong đó đã được duyệt hoặc được đưa vào training**. Bộ huấn luyện thực phải theo manifest đã lọc camera trên mặt nước, nhãn và nhóm nguồn. Không cộng các kho trùng nguồn thành số mẫu độc lập.

## Bảy nguồn người dùng cung cấp

| Nguồn | File/trạng thái thực | Quyết định sử dụng |
|---|---|---|
| **1. [Roboflow search drowning](https://universe.roboflow.com/search?q=class%3Adrowning)** | Đây là trang tìm kiếm, không có một archive duy nhất. Đã mở nhiều dự án và kiểm tra hai ứng viên export YOLOv8 chính thức; xem chi tiết dưới đây. **Chưa tải toàn bộ các dataset trong kết quả tìm kiếm.** | Chọn nguồn có giấy phép, view và khả năng tải thực; không mặc định mọi kết quả đều dùng được hoặc độc lập. |
| **2. [Kaggle Alanoud](https://www.kaggle.com/datasets/alanoudawaji/swimming-and-drowning-dataset)** | **Đã tải đầy đủ** `data/research/alanoud.zip`, 388.922.012 byte; đếm 9.997 ảnh + 9.997 labels YOLOv8, 18.506 box. README/YAML nhúng ghi **CC BY 4.0**, dẫn Roboflow Alanoud version 4. | Nguồn ảnh/label chính có thể tuyển chọn mở rộng. Loại underwater, stock/không rõ quyền và biến thể trùng; chia theo video/camera/scene. Không dùng nguyên split. Đã phát hiện phần lớn imagery gần Deep Rescue. |
| **3. [Figshare Underwater](https://figshare.com/articles/dataset/Underwater_Drowning_Detection_Dataset/29497235/2)** | Đã đọc trang/API metadata; **không tải ZIP 1,6 GB**. Chủ nguồn xác nhận camera underwater. | **Loại dữ liệu khỏi train/val/test/demo**, chỉ tham khảo cách định nghĩa nhãn và đánh giá. Không tải chỉ để tăng dung lượng/số ảnh. |
| **4. [randhana/Drowning-Detection-](https://github.com/randhana/Drowning-Detection-)** | **Đã tải đầy đủ repository ZIP** `data/research/randhana_repo.zip`, 118.213.901 byte, commit `3ec16b99f16e377901c1bb65193e378f299e9d2c`. ZIP có 40 entries, 12 MP4, `model.pth`, `lb.pkl` và Caffe model. LICENSE cấp kho MIT. | **Kiểm kê/tham khảo**; không execute/load weights. Chưa nhập bất cứ MP4 nào vào library/train/test: góc camera và quyền footage gốc không được MIT phần mềm tự xác minh. Có tên/cảnh underwater liên quan nguồn 5 nên không dùng nguyên kho. |
| **5. [Sensors / YOLO11-LiB](https://www.mdpi.com/1424-8220/25/17/5552)** | Bài báo không phải dataset; liên kết tác giả [Mibugi/Drowning-detection](https://github.com/Mibugi/Drowning-detection) có archive. **Đã tải đầy đủ** `data/research/mibugi.zip` — 101.111.276 byte, ghim commit `a417d924b9d906dc50ab3078dd48b0c5c63a0f1c`; 2.000 ảnh + 2.000 labels YOLO, CC BY 4.0 nhúng. | Tuyển chọn phần trên mặt nước và kiểm box/nguồn/duplicate trước train. Bản gốc trộn underwater; không dùng nguyên 2.000 ảnh và không gọi đã tải bản tăng cường 4.800 ảnh. `mibugi_v6.zip` là bản cùng checksum, **không phải dataset bổ sung**. |
| **6. [nweweq / Roboflow](https://universe.roboflow.com/nweweq/drowning-detection-rawzc-y0qr2)** | Đã mở overview: 264 ảnh, **0 dataset versions, 0 models**, CC BY 4.0. Chưa có archive export hoặc checkpoint công khai được xác minh. | Chưa tải thêm. Có thể khảo sát ảnh khi cần; không gọi API widget tổng quát là pretrained model của dự án này. |
| **7. [Springer / Intelligent Eyes on Water](https://link.springer.com/article/10.1007/s11227-025-07732-7)** | Đã đọc toàn văn, §5.1 mô tả camera underwater; dữ liệu dẫn Hydrosavex. **Không tải dataset underwater**. | Tham khảo temporal/event/alert architecture. Không dùng dữ liệu underwater hoặc số accuracy tác giả để chứng minh sản phẩm trên mặt nước. |

## Kiểm tra export hai ứng viên nguồn 1

Các liên kết dưới được lấy từ nút **Download/YOLOv8 trên trang version chính thức**, không đoán API key hoặc dùng tài khoản:

| Ứng viên | Quan sát công khai | Kết quả tải trong môi trường này |
|---|---|---|
| [DrowningDetectionTracking v2](https://universe.roboflow.com/drowningdetection-2zzxz/drowningdetectiontracking/dataset/2) | CC BY 4.0; trang version ghi 23.562 ảnh sau export/augmentation, trong khi overview 9.532 ảnh. Có augmentation đầu ra 3 bản/ảnh train. | Đã theo [export YOLOv8 chính thức](https://universe.roboflow.com/drowningdetection-2zzxz/drowningdetectiontracking/dataset/2/download/yolov8): web trả Cache miss/shell; HTTP trực tiếp **403 Forbidden**. Chưa nhận được ZIP hoặc URL ZIP công khai. |
| [Swimming and Drowning Detection / University v1](https://universe.roboflow.com/university-g3h71/swimming-and-drowning-detection/dataset/1) | CC BY 4.0; version ghi 12.365 ảnh sau xử lý, overview 7.295; augmentation flip/rotation/exposure. | Đã theo [export YOLOv8 chính thức](https://universe.roboflow.com/university-g3h71/swimming-and-drowning-detection/dataset/1/download/yolov8): web chỉ trả shell; HTTP trực tiếp **403 Forbidden**. Chưa nhận được ZIP hoặc URL ZIP công khai. |

Bằng chứng: `data/research/roboflow_export_checks.json`. Đây là kết quả truy cập tự động **trong môi trường này**, không đủ để kết luận dataset hoàn toàn không thể tải hoặc mọi người dùng đều bắt buộc đăng nhập. Không tìm thấy export ZIP không cần key/account qua các liên kết đã kiểm, nên chưa đánh dấu tải thành công. Không thử vượt xác thực hoặc đoán thông tin truy cập. Chưa có kiểm tra nội dung/overlap đầy đủ của hai archive này vì chưa tải được.

## Nguồn bổ sung đã có trong dự án

| File/nguồn | Nội dung đã xác minh | Vai trò |
|---|---|---|
| `data/research/deeprescue.zip` — [Kaggle Deep Rescue](https://www.kaggle.com/datasets/deeprescue/drowning-dataset) | 219.926.172 byte; 9.990 ảnh, COCO, 18.465 box. Kaggle khai CC0, COCO embedded ghi Unknown; trộn view và stock. | Raw tham khảo/tuyển chọn; không gộp với Alanoud như tập độc lập. Audit overlap cho thấy 9.969/9.997 ảnh Alanoud có tên gốc khớp; mẫu dHash xác nhận phần lớn imagery chung. |
| `data/research/nvbangg.zip` — [Kaggle drowning-test](https://www.kaggle.com/datasets/nvbangg/drowning-test) | 42.519.810 byte; 3 MP4 tên theo YouTube ID; metadata uploader MIT, quyền video gốc chưa xác minh. | Raw research, **không tự nhập library/train**. |
| `data/research/bhushankumarkashyap.zip` — [Kaggle drowning](https://www.kaggle.com/datasets/bhushankumarkashyap/drowning) | 49.486.629 byte; 3.877 ảnh crop, không phải YOLO bbox dataset; uploader Apache-2.0. | Chưa chọn train detector; còn thiếu kiểm view, nhãn và provenance. |
| `data/video_library.json` và `data/library/clips/` | **8 clip thật**, 264,5 giây; source/credit/license/cut/hash và annotations; nguồn DVIDS Public Domain và Commons CC BY-SA 4.0. | Library kiểm tra/demo, giữ ngoài training. Chỉ các đoạn above-water được chọn; có negative/diễn tập/cứu hộ thật, phân biệt fixed-view và motion stress. Xem `VIDEO_LIBRARY.md`. |

## Checksum archive thực

| File trong `data/research/` | SHA-256 |
|---|---|
| `alanoud.zip` | `54b20dcb7c85c9bf717938e7a5f61c81fbd75ec0af35ffbcc93891ca1bd9f9b1` |
| `mibugi.zip` và `mibugi_v6.zip` — cùng một nội dung | `95932efb0e59ab7b54f82ae2640830a4fa91ffe881b19a9d68aebc3f10f9262d` |
| `randhana_repo.zip` | `bbe055d16fbce01c4a4b12a46906589b1e57ce47afaafe1e56d12be1ad4e071f` |
| `deeprescue.zip` | `df4e71830bfa5850ec6be960da7cd7e8e76b2184a116bde215b0f0d8708e95a0` |
| `nvbangg.zip` | `1707c8dfbc59a6296d89514a42c7411af69c347dcd68b9f0ec34985f63b6e2bf` |
| `bhushankumarkashyap.zip` | `bd4151188fc51186ec5209c8fd3957d01007b267e59bf8867152e081f770aaa4` |

Metadata tải/kiểm kê: `data/research/training_downloads.json`, `randhana_repo_inventory.json`, `alanoud_audit.json`; quy trình duyệt/split và các mẫu bị loại nằm trong manifest/audit của từng dataset curated. Các ghi chú khảo sát cũ mô tả trạng thái trước khi tải đầy đủ cần được đọc cùng bảng coverage hiện tại này.
