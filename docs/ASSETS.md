# Tài nguyên tải về và nguồn gốc

Kiểm tra nguồn công khai ngày 28/10/2026. Chạy `python scripts/fetch_assets.py` để tải lại đúng tài nguyên; `data/asset_manifest.json` ghi dung lượng, URL và SHA-256 thực tế sau tải.

## Checkpoint cộng đồng

- Nguồn: [Bagsangbin/yolo8s-drowning-detection](https://huggingface.co/Bagsangbin/yolo8s-drowning-detection/tree/main), tệp gốc `yolo8s_drowning_detect.pt`, khoảng 22,5 MB.
- Revision cố định: `399ad3be040da0a0d7e0b4b2828bcc53177d42e6`.
- SHA-256 dự kiến: `6e8094468fa0294887a930bf18db9e7c5989a74d5e3c1753ec21c4d742e72c29`.
- Metadata của chủ kho khai báo **AGPL-3.0**. Đây là model cộng đồng; không phải mô hình tự huấn luyện trong dự án này.
- Model card còn nhiều mục chưa điền: chưa công bố đầy đủ dataset, nguồn video, góc đặt camera, split, chỉ số độc lập và tiêu chí nhãn. **Chưa xác minh checkpoint được huấn luyện chỉ bằng cảnh trên mặt nước.** Dự án không nhập dữ liệu underwater để huấn luyện/đánh giá/trình diễn. Giới hạn nguồn gốc checkpoint cần được giải quyết bằng dataset đã kiểm duyệt và fine-tuning trước khi có thể nghiệm thu toàn bộ yêu cầu dữ liệu.
- Đầu ra chỉ là nhãn hình ảnh do mô hình học được; không xác nhận tình trạng y khoa, khả năng cứu sống hoặc sự cố đuối nước thật.

## Footage cứu hộ thật

- [USBP Rescues Drowning Man](https://www.dvidshub.net/video/812817/usbp-rescues-drowning-man), Matthew Dyman / U.S. Customs and Border Protection; quay 01/09/2021 tại Imperial Beach, California; 1 phút 45 giây; mã VIRIN `210901-H-DO456-0701`.
- Trang DVIDS ghi **PUBLIC DOMAIN**, áp dụng [quy định sử dụng DVIDS](https://www.dvidshub.net/about/copyright). Giữ ghi công; không ngụ ý cơ quan hoặc người trong video chứng thực dự án.
- URL MP4 được lấy trực tiếp từ phần tử `source` của trang video, không suy đoán đường dẫn. Tệp lưu ở `data/examples/usbp_rescue_imperial_beach_2021.mp4`.
- Đây là nguồn phục vụ kiểm tra pipeline. Cần xem trực tiếp toàn bộ footage để xác nhận góc quay trên mặt nước, camera cố định/PTZ, khoảng thời gian hợp lệ và sự cắt cảnh. Không suy ra ground truth theo từng frame từ tiêu đề.
- Chưa xác minh video không nằm trong dữ liệu huấn luyện checkpoint. Vì vậy không gọi đây là kiểm thử tổng quát hóa độc lập, không tính accuracy/recall từ một video.

## Nguồn bị loại khỏi demo

[Drowning in 60 Seconds PSA](https://www.dvidshub.net/video/522681/drowning-60-seconds) không được tải bởi script. [Media kit chính thức USACE](https://corpslakes.erdc.dren.mil/employees/watersafety/pdfs/LJWNM%20Campaign%20Media%20Kit.pdf) xác nhận có góc quay từ dưới nước và cảnh hồi tưởng. Không dùng nguyên video cho training, test hoặc demo theo phạm vi người dùng.

Không có bộ dữ liệu huấn luyện nào được nhập chỉ vì có tên drowning. Danh mục và quyết định sàng lọc nằm trong `DATA_RESEARCH.md`.

## Archive nghiên cứu bổ sung

`python scripts/fetch_assets.py --research-data` tải lại ba archive Kaggle đã khảo sát theo URL và SHA-256 trong `docs/sources.json`, đồng thời ghi manifest. Đây là dữ liệu thô **chưa được tự động cho phép vào train**. Deep Rescue có license uploader CC0 nhưng COCO embedded Unknown và ảnh stock/underwater cần loại; hai archive còn lại chưa được duyệt nguồn video/góc camera. Chỉ tập accepted do quy trình review/split tạo ra mới dùng cho fine-tuning.

Theo điều khoản DVIDS, ghi chú sử dụng footage: “The appearance of U.S. Department of War (DoW) visual information does not imply or constitute DoW endorsement.”
