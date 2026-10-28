# Bộ dữ liệu surface_v3 dùng cho lần huấn luyện mở rộng

Ngày chốt: 28/10/2026. Dataset: **`data/curated/surface_v3/data.yaml`**. Phạm vi là camera quan sát **từ phía trên mặt nước**, gồm người còn nổi hoặc đã chìm nhưng vẫn nhìn từ bờ/trên cao. Không dùng footage từ camera đặt dưới nước.

Đã thay bộ thí nghiệm 192 ảnh bằng **1.118 ảnh đã duyệt**, trong đó **812 train, 137 validation, 169 test**. Số ảnh train tăng từ 121 lên 812, khoảng **6,71 lần**, và thêm nhiều cảnh/camera. Đây là bằng chứng mở rộng dữ liệu; hiệu quả model phải xác định bằng kết quả đo sau huấn luyện.

## Từ archive gốc đến dữ liệu được giữ

| Bước thực sự đã làm | Số ảnh/biến thể |
| --- | ---: |
| Alanoud archive đã tải đầy đủ | 9.997 |
| Mibugi archive đã tải đầy đủ, ghim commit | 2.000 |
| Tổng entry ảnh hai archive, chưa coi là mẫu độc lập | **11.997** |
| Loại nguồn có tên stock/phim rõ | −370 |
| Ngoài whitelist camera/nguồn bảo thủ | −5.317 |
| Source class không tương thích, không tự bỏ box dương tính | −18 |
| Chọn một biến thể/tên frame gốc, bỏ bản lặp trong export | −4.649 |
| Biến thể tốt nhất vẫn xoay/viền đen/biến màu/grayscale quá mức | −255 |
| Candidate được xem trực tiếp từng ảnh kèm bounding boxes | **1.388** |
| Bị loại sau khi xem và audit | **−270** |
| Dataset cuối | **1.118** |

Whitelist là bước tuyển chọn bảo thủ. Không khẳng định 5.317 ảnh ngoài whitelist đều là underwater hoặc đều sai; chúng chưa được phê duyệt cho phiên bản này. DeepRescue không được cộng thêm vào 11.997 vì imagery trùng phần lớn với Alanoud.

Đã xem **toàn bộ 44 contact sheet**, ID 0–1387: agent chính xem 384 candidate, agent dữ liệu xem 1.004 candidate. Quyết định được lưu theo từng ảnh và reviewer. Việc xem kiểm tra góc camera, nguồn rõ ràng có vấn đề và độ hợp lý hình học của box; **không phải gán nhãn y khoa độc lập**.

| Nhóm lý do chính sau review | Candidate bị loại |
| --- | ---: |
| Stock/ảnh tĩnh không rõ nguồn/watermark hoặc nguồn ảnh quá yếu | 94 |
| Nhãn drowning hàng loạt cho các bathers, mâu thuẫn với clip liên quan | 67 |
| Xoay/đảo ảnh/viền đen giả | 51 |
| Overlay đã chỉ điểm mục tiêu, có nguy cơ học cue của nhãn | 25 |
| Biến màu giả rõ | 16 |
| Box gần toàn frame, bao nhiều nước/nền | 8 |
| Frame/crop trùng hoặc tương ứng nhưng nhãn drowning/swimming đối nghịch | 6 |
| Camera dưới nước xác định trực tiếp trong candidate | 3 |
| **Tổng** | **270** |

Đây là phân loại theo lý do quyết định chính của 270 candidate; không phải ước lượng tổng số ảnh underwater/stock trong mọi archive. Các mẫu bất hợp lệ nằm ngoài whitelist đã bị loại trước đó.

## Nhãn, nguồn và chia tập cuối

Canonical class ID: **0=`drowning`, 1=`swimming`**. Đã giữ **283 ảnh từ Alanoud và 835 ảnh từ Mibugi**. Không tạo thêm nhãn giả và không tự biến ba video nvbangg thành dữ liệu supervised.

| Split | Ảnh | Box `drowning` | Box `swimming` |
| --- | ---: | ---: | ---: |
| Train | **812** | **448** | **758** |
| Validation | **137** | **60** | **150** |
| Test | **169** | **64** | **239** |

| Nhóm cảnh bảo thủ | Ảnh | Split |
| --- | ---: | --- |
| Indoor training pool, toàn bộ IMG_3607–IMG_3611 gộp cùng pool/phiên | 405 | train |
| Waterpark main, gộp các tên clip cùng cảnh | 201 | train |
| Stadium camera, người bơi bình thường/mục tiêu nhỏ | 80 | train |
| Large indoor pool training, gộp camera rộng/crop liên quan | 54 | train |
| Numbered pool candidates được duyệt | 39 | train |
| Open-water aerial/shore sequence được duyệt | 21 | train |
| Outdoor waterpark demonstration | 9 | train |
| Wave pool | 3 | train |
| Outdoor resort pool mới, giữ cả scene ngoài train | 80 | validation |
| High pool cũ, mọi biến thể `video_2022-12-07_23-08-*` | 57 | validation |
| Competition pool CCTV mới, gồm tên 998/999 và 1000+ | 102 | test |
| Indoor other CCTV mới, mọi clip cùng pool có dấu hiệu nguy cơ | 67 | test |

Test mới có cả người bơi bình thường và nhãn nguy cơ, thay cho bản chuẩn bị surface_v2 chỉ có test âm tính. Tên số 998/999 đã được chuyển sang đúng group test sau khi nhìn thấy cùng camera với 1000+, tránh rò rỉ do ranh giới tên file.

## Bảo vệ các lần đánh giá cũ và lựa chọn holdout mới

- **Không thay đổi** dataset `deeprescue_v1`, 43 ảnh validation/28 ảnh test cũ hoặc khóa đánh giá của nó.
- Toàn bộ scene `high_pool` cũ tiếp tục ngoài train, dù ảnh có tên/re-export khác. Scene `indoor_pool` của test cũ cũng không xuất hiện trong train mới.
- Dataset `surface_v2` được giữ nguyên. Agent chính đã dừng lần chạy của nó trong epoch đầu và ghi `interrupted`; không lấy checkpoint dở đó để huấn luyện tiếp surface_v3.
- Trước lần train cuối, chuyển **toàn bộ 67 ảnh của scene mới `indoor_other_cctv`** sang test. Không tách frame liền kề của cùng pool giữa train/test. Lần train cuối bắt đầu từ **checkpoint COCO gốc**, không từ weights surface_v2 đã xem scene đó.
- Đã sàng lọc dHash train surface_v3 so với mọi ảnh val/test legacy: **812 × 71 cặp, không có cặp Hamming ≤4**. Kết quả lưu `data/reviews/surface_v3_legacy_overlap_audit.json`. Đây là kiểm tra bổ sung, không chứng minh tuyệt đối mọi video/camera đều độc lập.
- Audit dataset không phát hiện SHA-256 hoặc dHash bằng nhau qua split. Frame gần trùng trong cùng một split vẫn có thể tồn tại; **số ảnh không phải số tai nạn độc lập**.

Ảnh test đã được xem khi kiểm duyệt chất lượng. Không gọi đây là đánh giá mù của bên thứ ba, hoặc bộ nhãn drowning được xác nhận y khoa. Những kết quả legacy phải ghi là legacy đã từng được xem; không đổi tên thành test ngoài hoàn toàn mới.

## Trạng thái bảy nguồn người dùng cung cấp

| Nguồn bắt buộc | Trạng thái tải/khảo sát và cách dùng |
| --- | --- |
| [1. Roboflow search drowning](https://universe.roboflow.com/search?q=class%3Adrowning) | Là trang tìm kiếm, đã mở nhiều dự án riêng. Một số dự án có version, nhưng export miễn phí không cần tài khoản/key chưa được xác minh cho tất cả; không tự coi widget API là file tải. Hai archive nguồn 2/5 đã tải chính là export Roboflow được phân phối lại, được audit thay vì cộng số ảnh của trang tìm kiếm |
| [2. Alanoud/Kaggle](https://www.kaggle.com/datasets/alanoudawaji/swimming-and-drowning-dataset) | **Tải đầy đủ** 388.922.012 byte; 9.997 ảnh và 9.997 nhãn YOLO. Metadata archive CC BY 4.0; tuyển chọn 283 ảnh, chuẩn hóa lớp và chia lại theo scene |
| [3. Figshare underwater](https://figshare.com/articles/dataset/Underwater_Drowning_Detection_Dataset/29497235) | Đọc metadata: chủ nguồn xác nhận camera underwater; **loại dữ liệu**, không tải ZIP ~1,6 GB để train/demo. Chỉ tham khảo taxonomy/phương pháp |
| [4. randhana/GitHub](https://github.com/randhana/Drowning-Detection-) | Đã kiểm tree, README, code, MIT, model và danh sách 12 MP4 có thật. Không có bộ bbox train đầy đủ/provenance từng video; thuật toán khoảng cách người <50 px không đủ căn cứ nguy cơ. Chưa nhập làm dữ liệu detector; video phải kiểm view/quyền/nhãn riêng |
| [5. Sensors và kho Mibugi](https://www.mdpi.com/1424-8220/25/17/5552) | **Tải đầy đủ** [ZIP tác giả ghim commit](https://raw.githubusercontent.com/Mibugi/Drowning-detection/a417d924b9d906dc50ab3078dd48b0c5c63a0f1c/datasets/Drowning%20Detect.v6-2000.yolov11.zip), 101.111.276 byte, 2.000 ảnh +2.000 label. CC BY 4.0 trong README/YAML; tuyển chọn 835 ảnh, loại underwater/stock/nhãn kém. Code/weights trong repo có tình trạng license riêng, không suy ra từ license dataset |
| [6. nweweq/Roboflow](https://universe.roboflow.com/nweweq/drowning-detection-rawzc-y0qr2) | Trang ghi 264 ảnh, **0 version và 0 model** tại lần kiểm tra; chưa có export có thể tải được xác minh. Không tuyên bố đã tải/train trên nguồn này |
| [7. Intelligent eyes on water/Springer](https://link.springer.com/article/10.1007/s11227-025-07732-7) | Đã đọc nghiên cứu, §5.1 mô tả camera underwater/Hydrosavex. **Không dùng dữ liệu underwater**; chỉ tham khảo tracking/cảnh báo, không áp mAP tác giả cho hệ thống |

Các nguồn đầy đủ đã tải khác: DeepRescue COCO được giữ để đối chiếu overlap; nvbangg gồm ba MP4 chưa có bbox/event labels; archive bhushankumarkashyap gồm ảnh crop chưa đủ bbox/view/provenance cho detector này. “Tải mọi nguồn có thể dùng” không có nghĩa nhập dữ liệu camera dưới nước, dữ liệu chưa có quyền hoặc những export trùng lặp vào train.

## Attribution, cấu hình và bằng chứng

Hai nguồn ảnh sử dụng khai báo **CC BY 4.0** trong archive. Giữ tên người phát hành, URL, version, giấy phép và mô tả thay đổi: lọc view/nguồn, bỏ biến thể, chuẩn hóa class, loại nhãn mâu thuẫn và chia lại theo scene. Việc uploader công bố license không tự xác minh quyền với mọi footage bên thứ ba; các mẫu stock/phim nhìn thấy đã bị loại, provenance chưa rõ vẫn cần ghi nhận.

Mibugi ZIP SHA-256: `95932efb0e59ab7b54f82ae2640830a4fa91ffe881b19a9d68aebc3f10f9262d`; Alanoud ZIP SHA-256: `54b20dcb7c85c9bf717938e7a5f61c81fbd75ec0af35ffbcc93891ca1bd9f9b1`. `mibugi_v6.zip` là hard link của `mibugi.zip`, không phải dataset thứ hai.

Bằng chứng chính:

- `data/research/training_downloads.json`: URL tải thực, kích thước và hash.
- `data/reviews/surface_v2_sheets/`: toàn bộ 44 contact sheet, tiếp tục dùng cho cùng ảnh surface_v3.
- `data/reviews/surface_v3_decisions.json`, `surface_v3.csv`: mọi quyết định và split cuối.
- `data/curated/surface_v3/audit.json`, `manifest.json`, `data.yaml`: dataset thật được đưa vào train, có hash ảnh/nhãn.
- `scripts/download_training_sources.py`, `prepare_surface_dataset.py`, `audit_dataset.py`: tái hiện tải/chọn/xuất/kiểm tra.
- Tám kiểm thử logic lọc và group đã đạt: chống underwater, group qua split, ảnh trùng qua split, box NaN, camera legacy, ranh giới 998/999, năm clip cùng pool và tên stock/phim.

Không chỉnh dataset đã audit trong khi train. Mọi lần huấn luyện, checkpoint đầu/cuối, metrics validation/test và threshold phải có record riêng. Detector ảnh không tự giải quyết người mất dấu/chìm: sản phẩm vẫn cần tracking, kiểm tra camera chuyển động, lịch sử bằng chứng và đánh giá sự kiện theo thời gian trên video phù hợp.
