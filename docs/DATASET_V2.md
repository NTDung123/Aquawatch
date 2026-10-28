# Dữ liệu huấn luyện trên mặt nước, surface_v2 và surface_v3

Ngày thực hiện: 28/10/2026. Đây là bộ dữ liệu ảnh đã được sàng lọc để huấn luyện detector, không phải bộ video có nhãn sự kiện hoặc bằng chứng xác nhận tình trạng y khoa.

## Phiên bản cuối dùng cho huấn luyện: surface_v3

**Dataset cuối: `data/curated/surface_v3/data.yaml`.** Giữ nguyên 1.118 ảnh đã duyệt, nhưng chuyển **toàn bộ cảnh mới `indoor_other_cctv` gồm 67 ảnh** từ train sang test trước lần huấn luyện cuối. Việc này bổ sung test dương tính và giữ toàn bộ clip cùng pool trong một split.

| Split cuối | Ảnh | Box `drowning` | Box `swimming` |
| --- | ---: | ---: | ---: |
| Train | **812** | **448** | **758** |
| Validation | **137** | **60** | **150** |
| Test | **169** | **64** | **239** |

Test cuối gồm camera competition pool bình thường (102 ảnh) và cảnh indoor mới có dấu hiệu nguy cơ (67 ảnh). Cảnh test mới này tách khỏi lần fine-tune cuối; dữ liệu vẫn là nhãn ảnh proxy, nên mAP không thay thế event recall. `high_pool` và `indoor_pool` của đánh giá cũ tiếp tục ở ngoài train; không thay dữ liệu/khóa test cũ.

Lần chạy thăm dò `surface_v2` đã được agent chính dừng trong epoch đầu và ghi trạng thái interrupted. **Không dùng trọng số lần chạy đó để khởi tạo surface_v3**. Lần huấn luyện cuối bắt đầu lại từ checkpoint COCO gốc, sau khi chốt chia tập surface_v3; dataset surface_v2 được giữ nguyên để truy vết. Đã xem ảnh test trong quá trình kiểm duyệt dữ liệu, nên không mô tả đây là một đánh giá mù do bên thứ ba thực hiện.

Quyết định/cấu hình cuối nằm trong `data/reviews/surface_v3_decisions.json`, `surface_v3.csv`, `data/curated/surface_v3/audit.json` và `manifest.json`. Không sửa những tệp này trong lúc huấn luyện. Có thể tái tạo trên workspace chưa có đầu ra bằng:

```powershell
.venv\Scripts\python.exe scripts/prepare_surface_dataset.py build --version surface_v3 --decisions data/reviews/surface_v3_decisions.json
.venv\Scripts\python.exe scripts/audit_dataset.py build --source-root data/raw/surface_v3 --review data/reviews/surface_v3.csv --output data/curated/surface_v3 --classes drowning swimming
```

Các mục dưới đây giữ lại snapshot chuẩn bị **surface_v2**; bảng chia tập trên là cấu hình cuối **surface_v3**.

## Kết quả thực hiện

Đã tải toàn bộ archive nguồn tác giả Mibugi và kiểm tra các archive nguồn liên quan đã có. Sau khi đối chiếu nguồn, chọn một biến thể cho mỗi tên frame gốc, áp dụng whitelist camera và xem **toàn bộ 1.388 candidate kèm bounding boxes**, bộ `data/curated/surface_v2/` giữ **1.118 ảnh**: **879 train, 137 validation, 102 test**.

1.004 candidate do agent phụ trách dữ liệu xem trực tiếp; 384 candidate (ID 448–831) do agent chính xem trực tiếp. Quyết định cụ thể của mỗi ảnh nằm trong `data/reviews/surface_v2_decisions.json`. Đã loại **270 candidate** do stock/quyền nguồn chưa rõ, camera dưới nước, box gần toàn frame, biến màu/đảo ảnh, nhãn mâu thuẫn hoặc nhiễm thông tin nhãn từ overlay.

| Split | Ảnh | Box `drowning` | Box `swimming` | Diễn giải |
| --- | ---: | ---: | ---: | --- |
| Train | 879 | 512 | 772 | Có cả dấu hiệu nguy cơ và người bơi bình thường; 9 nhóm cảnh bảo thủ |
| Validation | 137 | 60 | 150 | Pool góc cao cũ và resort ngoài trời giữ ngoài train |
| Test mới | 102 | 0 | 225 | Camera bể thi đấu, chỉ có người bơi bình thường: dùng kiểm tra false positives, **không tính được drowning recall** trên nhóm này |

Số ảnh train tăng từ **121** ở thí nghiệm cũ lên **879**, khoảng **7,26 lần**. Đây là tăng quy mô và cảnh huấn luyện; chưa tự chứng minh model mới chính xác hơn. Kết quả cần đo sau huấn luyện, tách metrics ảnh khỏi metrics cảnh báo theo thời gian.

## Archive đã tải và nguồn sử dụng

| Nguồn | Archive thực | Quy mô xác minh | Trạng thái |
| --- | --- | --- | --- |
| [Alanoud: Swimming and Drowning](https://www.kaggle.com/datasets/alanoudawaji/swimming-and-drowning-dataset) | `data/research/alanoud.zip`, 388.922.012 byte | 9.997 ảnh thực và 9.997 label; README/YAML nhúng CC BY 4.0 | Giữ **283 ảnh** sau lọc; bỏ split gốc vì cùng video qua nhiều split |
| [Kho tác giả bài Sensors, Mibugi](https://github.com/Mibugi/Drowning-detection) | `data/research/mibugi.zip`, 101.111.276 byte; `mibugi_v6.zip` là hard link cùng dữ liệu | 2.000 ảnh và 2.000 label; README/YAML nhúng CC BY 4.0 | Giữ **835 ảnh** sau lọc, gồm nhiều scene mới |
| [DeepRescue](https://www.kaggle.com/datasets/deeprescue/drowning-dataset) | `data/research/deeprescue.zip`, 219.926.172 byte | 9.990 ảnh COCO | Chỉ dùng đối chiếu nguồn gốc và overlap; **không cộng lại** số ảnh như nguồn độc lập |
| [nvbangg/drowning-test](https://www.kaggle.com/datasets/nvbangg/drowning-test) | `data/research/nvbangg.zip`, 42.519.810 byte | Ba MP4; không có label bbox ảnh | Dành cho khảo sát video; không tự biến thành dữ liệu supervised bằng nhãn đoán |

Tệp [training_downloads.json](../data/research/training_downloads.json) ghi URL, kích thước, SHA-256 và trạng thái tải thực. Mibugi được ghim commit `a417d924b9d906dc50ab3078dd48b0c5c63a0f1c`, Git blob `48ff50d2f5d9cf9fab7d08dee68d377d4848bc4b`. SHA-256 archive Mibugi là `95932efb0e59ab7b54f82ae2640830a4fa91ffe881b19a9d68aebc3f10f9262d`.

Không tải dữ liệu chỉ quay từ camera dưới nước để rồi đưa vào train. Nguồn không có export công khai hoặc yêu cầu quyền/tài khoản riêng được ghi nhận riêng; việc tải các archive trên không có nghĩa đã truy cập mọi dataset trên Roboflow.

## Chia tập và bảo vệ tập đánh giá cũ

| Nhóm cảnh | Ảnh giữ | Split |
| --- | ---: | --- |
| Indoor training pool: toàn bộ IMG_3607 đến IMG_3611 cùng một pool/phiên | 405 | train |
| Waterpark main: mọi clip cùng camera/cảnh, các tên khác nhau được gộp | 201 | train |
| Indoor other CCTV/demonstration, gộp các clip cùng pool | 67 | train |
| Stadium camera: người bơi bình thường, mục tiêu nhỏ | 80 | train |
| Large indoor pool training, gộp camera rộng/crop cùng scene | 54 | train |
| Numbered pool candidates đã duyệt | 39 | train |
| Open-water aerial/shore sequence đã duyệt | 21 | train |
| Outdoor waterpark demonstration | 9 | train |
| Wave-pool frame sạch được duyệt | 3 | train |
| Outdoor resort pool | 80 | validation |
| High pool: toàn bộ các clip `video_2022-12-07_23-08-*` | 57 | validation |
| Competition pool CCTV, gồm tên số 998/999 và 1000+ | 102 | test |

Nhóm `high_pool` đã tồn tại trong validation cũ, tuyệt đối không đưa biến thể/frame của nó vào train. Cảnh `indoor_pool` của test cũ cũng giữ hoàn toàn ngoài train; dữ liệu và khóa test trong `deeprescue_v1` không bị thay đổi. Test mới competition pool chỉ có mẫu bình thường; kiểm tra bỏ sót nguy cơ cần thêm video/sự kiện dương tính có nhãn hoặc báo riêng kết quả legacy test đã từng được xem.

Trong lúc duyệt phát hiện tên số 998 và 999 thực ra cùng camera với nhóm 1000+, dù quy tắc tên sơ bộ xếp vào train. Đã sửa **cả nhóm cảnh** sang test trước huấn luyện. Điều này cho thấy chia theo tên file đơn thuần không đủ, cần kiểm tra hình ảnh thực.

## Cách lọc và kiểm tra nhãn

- Loại theo tên nguồn rõ ràng là stock/phim; phần còn lại vẫn xem ảnh vì tên số không chứng minh nguồn sạch. Đã loại thêm watermark iStock/Getty/Dreamstime thấy trong ảnh.
- Camera trên mặt nước được xem trực tiếp ở từng candidate giữ lại. Người chìm nhìn từ bờ vẫn hợp lệ; camera dưới mặt nước và góc nhìn không rõ bị loại.
- Loại biến thể đảo ngược, màu giả mạnh, frame có cue nhãn đã vẽ sẵn. Cảnh news có vòng tròn đánh dấu sự cố không được đưa vào whitelist train.
- Chuẩn hóa class ID **0=`drowning`, 1=`swimming`** từ hai nguồn. Không âm thầm bỏ một box dương tính không tương thích; proposal loại ảnh có source class ngoài hai lớp này.
- Một frame gốc chỉ chọn một biến thể xuất; Alanoud và DeepRescue phần lớn trùng nguồn nên không gộp thành hai bộ mẫu độc lập.
- Loại những frame waterpark gán `drowning` hàng loạt cho nhiều người bơi bình thường, mâu thuẫn với clip khác trong cùng cảnh; không tự đổi thành nhãn mới khi chưa có video/ground truth đủ.
- Audit bắt được một cặp **ảnh trùng byte nhưng nhãn đối nghịch** (candidate 1236/1237). Đã loại cả cặp và các crop tương ứng mâu thuẫn rõ khác, tổng sáu frame/crop; không tùy ý chọn nhãn có lợi cho model.
- Audit cuối kiểm tra ảnh giải mã được, bbox YOLO hợp lệ, nguồn/license, group không qua nhiều split, SHA-256 và dHash. Không có SHA-256 trùng hoặc dHash bằng nhau **qua split**. Có **54 nhóm dHash bằng nhau trong cùng split**; nhiều frame gần nhau vẫn có thể tồn tại, nên số ảnh không phải số sự cố độc lập.

Box được xem về góc camera và độ hợp lý hình học, không xác minh đầy đủ ý nghĩa hành vi của mọi nhãn. Các nhãn nguồn vẫn có thể thiếu đối tượng, lẫn bơi/chơi nước/cầu cứu hoặc không phân biệt được hành động từ một frame. Bản dữ liệu này phù hợp làm thí nghiệm detector có giới hạn; không phải bộ nhãn y khoa đã chứng nhận.

## Bằng chứng và tái hiện

- `scripts/download_training_sources.py`: tải miễn phí public URL và kiểm hash/size, không dùng secret.
- `scripts/prepare_surface_dataset.py`: tạo candidate, chọn biến thể, render contact sheets và xuất ảnh/label đã duyệt.
- `data/reviews/surface_v2_proposal.json`: số lượng nguồn, whitelist, biến thể bị gộp và lý do lọc ban đầu.
- `data/reviews/surface_v2_sheets/sheet_000.jpg` đến `sheet_043.jpg`: toàn bộ candidate cùng box.
- `data/reviews/surface_v2_decisions.json`: quyết định từng candidate, reviewer, góc camera và lý do.
- `data/reviews/surface_v2.csv`: input kiểm duyệt cho bước build; bản trước duplicate audit được giữ riêng.
- `data/reviews/surface_v2_review_summary.json`: số liệu tổng hợp quá trình duyệt.
- `data/curated/surface_v2/audit.json`, `manifest.json`, `data.yaml`: bằng chứng bộ dữ liệu thật đưa vào huấn luyện.

```powershell
.venv\Scripts\python.exe scripts/download_training_sources.py --direct
.venv\Scripts\python.exe scripts/prepare_surface_dataset.py propose
```

`propose` chỉ dùng trên bản workspace chưa có file quyết định; không ghi đè các quyết định hiện có. Sau khi hoàn tất mọi review trong JSON, `build` xuất raw dataset vào thư mục phiên bản mới. Bản dữ liệu đã xây dựng hiện tại không cần chạy lại.

```powershell
.venv\Scripts\python.exe scripts/prepare_surface_dataset.py build
.venv\Scripts\python.exe scripts/audit_dataset.py build --source-root data/raw/surface_v2 --review data/reviews/surface_v2.csv --output data/curated/surface_v2 --classes drowning swimming
```

Lệnh build từ chối ghi đè dữ liệu phiên bản đã có. Khi thay quyết định hoặc bổ sung nguồn, phải tạo phiên bản mới và giữ audit cũ.

## Giấy phép và giới hạn

Hai nguồn ảnh dùng khai báo **CC BY 4.0** trong archive. Cần giữ URL, tên người phát hành, version, ghi thay đổi lọc/chuyển nhãn và attribution khi chia sẻ bộ dữ liệu hoặc sản phẩm liên quan. Việc nguồn khai báo giấy phép không tự xác minh quyền với mọi footage bên thứ ba; những mẫu stock/phim thấy rõ đã bị loại, phần provenance còn thiếu phải tiếp tục ghi nhận.

Generic COCO initializer giúp tránh phụ thuộc vào nguồn huấn luyện không rõ của checkpoint drowning cộng đồng. Tuy vậy vẫn phải ghi chính xác checkpoint khởi tạo và tập train của từng lần chạy, không tuyên bố mọi nguồn video đã được chứng minh hoàn toàn độc lập với mọi dạng pretraining. Bài toán cuối cùng vẫn cần đánh giá theo video có ground truth thời gian, camera đúng phạm vi, false alarms/hour và detection latency.
