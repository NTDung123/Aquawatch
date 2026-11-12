# Nguồn và giấy phép thành phần

| Thành phần | Nguồn / giấy phép do chủ nguồn công bố |
|---|---|
| Ultralytics / YOLOv8 | [Ultralytics licensing](https://www.ultralytics.com/license), AGPL-3.0. Checkpoint triển khai `surface_v4` tiếp tục từ V3 khởi tạo YOLOv8s COCO; thông tin huấn luyện và SHA-256 ở `data/training_record.json` và `docs/TRAINING.md`. |
| Checkpoint cộng đồng tùy chọn | [Hugging Face model repository](https://huggingface.co/Bagsangbin/yolo8s-drowning-detection/tree/main), metadata AGPL-3.0. Đây là baseline tải bằng `--baseline`, khác checkpoint fine-tune đang triển khai. |
| PyTorch / torchvision | [PyTorch](https://github.com/pytorch/pytorch/blob/main/LICENSE), [torchvision](https://github.com/pytorch/vision/blob/main/LICENSE), BSD-style |
| FastAPI | [MIT](https://github.com/fastapi/fastapi/blob/master/LICENSE) |
| OpenCV | [OpenCV license](https://opencv.org/license/), Apache-2.0 cho các bản hiện hành |
| Footage USBP/DVIDS | Trang nguồn ghi Public Domain; ghi công Matthew Dyman/U.S. Customs and Border Protection. Không ngụ ý cơ quan này chứng thực dự án. Điều khoản và URL trong `docs/ASSETS.md`. |
| Tập con Deep Rescue | Kaggle uploader khai CC0; COCO embedded metadata ghi Unknown; quyền footage/ảnh gốc chưa xác minh đầy đủ. Đã loại ảnh stock/watermark/underwater trong tập con duyệt; chỉ dùng thăm dò local, không trình bày như dataset đã xác nhận toàn bộ quyền. |
| Lecture1–4 | Người dùng cung cấp để nghiên cứu học phần; không áp giấy phép nguồn mở cho bài giảng. Không sửa tệp gốc. |
| Video mẫu CCTV Lifeguard Rescue | Tải theo yêu cầu từ archive Kaggle được ghim trong `scripts/fetch_cctv_library.py`; uploader khai MIT, quyền footage gốc chưa được xác minh riêng. Repo chứa cấu hình đoạn đã duyệt, không kèm các tệp video. Xem `docs/VIDEO_LIBRARY.md`. |

Giữ license/thông báo bản quyền kèm các gói trong `.venv/Lib/site-packages`. Mã nguồn và checkpoint fine-tune được đồng bộ tại [NTDung123/Aquawatch](https://github.com/NTDung123/Aquawatch); thư viện bên thứ ba vẫn tuân theo giấy phép tương ứng. Dữ liệu train, video gốc và kết quả cá nhân không nằm trong bản mã nguồn.
