# Rà soát bổ sung dữ liệu trên mặt nước

Ngày kiểm tra: 28/10/2026. Đã xuất **`data/curated/surface_v4/data.yaml`**: **1.313 ảnh**, gồm **1.007 train / 137 validation / 169 test**. Bộ này thêm **195 ảnh train đã duyệt** so với `surface_v3`; train tăng **24,0%** so với v3 và **8,32 lần** so với 121 ảnh train của thí nghiệm 192 ảnh ban đầu. Không ghi đè bộ cũ hoặc đưa các biến thể của cảnh đánh giá vào train. Audit đã đạt, không có lỗi.

| Split cuối | Ảnh | Box drowning | Box swimming |
| --- | ---: | ---: | ---: |
| Train | **1.007** | **559** | **917** |
| Validation | **137** | **60** | **150** |
| Test | **169** | **64** | **239** |

Số ảnh tăng là kết quả mở rộng dữ liệu, không phải bằng chứng model đã tốt hơn. Kết quả huấn luyện/validation/test phải được đọc từ record của từng lần chạy.

## Dữ liệu thực đã có

- Alanoud/Kaggle: archive đầy đủ `data/research/alanoud.zip`, **388.922.012 byte**, 9.997 ảnh và 9.997 nhãn YOLO. SHA-256 `54b20dcb7c85c9bf717938e7a5f61c81fbd75ec0af35ffbcc93891ca1bd9f9b1`.
- Mibugi/tác giả Sensors: archive đầy đủ `data/research/mibugi.zip`, **101.111.276 byte**, 2.000 ảnh và 2.000 nhãn YOLO. SHA-256 `95932efb0e59ab7b54f82ae2640830a4fa91ffe881b19a9d68aebc3f10f9262d`. `mibugi_v6.zip` là hard link của cùng archive, không tính hai lần.
- Cả hai archive có metadata **CC BY 4.0**. Nguồn Mibugi được ghim commit `a417d924b9d906dc50ab3078dd48b0c5c63a0f1c`; [ZIP công khai chính xác](https://raw.githubusercontent.com/Mibugi/Drowning-detection/a417d924b9d906dc50ab3078dd48b0c5c63a0f1c/datasets/Drowning%20Detect.v6-2000.yolov11.zip). Các archive và lịch sử tải có trong `data/research/training_downloads.json`.
- DeepRescue được giữ để đối chiếu overlap, không cộng imagery trùng vào train. Ba video nvbangg không có bbox/event annotation nên không tự biến thành dữ liệu supervised. Tình trạng đủ bảy nguồn và lỗi export Roboflow thực tế được ghi trong `docs/DATASET_V3.md` và `docs/DOWNLOAD_COVERAGE.md`.

Nguồn công bố license không tự xác minh quyền với tất cả footage bên thứ ba. Loại mẫu thấy stock watermark/phim; không suy ra license code/weights từ license archive ảnh. Không tải lại archive đã đầy đủ để tạo cảm giác tăng dữ liệu.

## Lần mở rộng này khác whitelist ban đầu

`scripts/build_expanded_dataset.py discover` quét các tên frame gốc chưa được xử lý bởi whitelist/review v3. Chọn một biến thể chất lượng tự nhiên cho mỗi tên gốc, không nhân bản export/augmentation. Kết quả kiểm kê khép kín trên **11.997 entry ảnh** của hai nguồn:

| Nhánh xử lý | Entry ảnh/biến thể |
| --- | ---: |
| Đã được xử lý bởi group/decision của surface_v3 | 6.310 |
| Tên stock/phim rõ | 370 |
| Nhãn mixed/noncanonical không thể giữ mà bỏ target box | 392 |
| Biến thể cùng tên frame được gộp | 3.282 |
| Biến thể tốt nhất vẫn viền đen/tint/grayscale quá mức | 104 |
| Candidate bổ sung có ảnh/box để review trực tiếp | **1.539** |
| **Tổng** | **11.997** |

Đây là số entry và tên ảnh nguồn, không phải số sự kiện/camera độc lập. Các ảnh trong nhánh đầu giữ nguyên kết quả review trước; không khẳng định mỗi entry biến thể được xem lại riêng.

Toàn bộ candidate bổ sung có tại `data/reviews/expanded_v4_candidates/`, 65 sheet `expanded_v4_sheets/sheet_000.jpg`–`sheet_064.jpg` và metadata `expanded_v4_decisions.json`. Đã xem **tất cả 1.539 ảnh kèm box**, chia công việc 960/240/339 candidate cho ba reviewer. Frontend reviewer mở thêm mọi ảnh tĩnh được duyệt ở kích thước đầy đủ và kiểm các watermark/góc nhìn nghi ngờ. Quyết định ghi trạng thái, góc camera, source group, split, reviewer và lý do; **không tự gán lại nhãn drowning/swimming theo phỏng đoán y khoa**.

Kết quả review ban đầu giữ 200 ảnh; loại thêm **5 frame gần trùng** sau sàng lọc perceptual, còn **195 được giữ / 1.344 bị loại / 0 pending**. Trong 195 ảnh mới, **164 từ Mibugi, 31 từ Alanoud**, thêm **111 box drowning và 159 box swimming**. Cộng cả review v3 là **2.927 candidate thực sự được xem**, giữ 1.313; không gọi mọi entry augmentation trong hai archive là ảnh độc lập được duyệt.

| Phần train được bổ sung | Ảnh mới |
| --- | ---: |
| Các đoạn bài học bơi quay từ trên mặt nước, gộp group nguồn bảo thủ | 139 |
| Waterpark main, cùng group train đã biết | 10 |
| Open-water aerial/shore swimming, cùng group train đã biết | 8 |
| Overhead lane pool | 1 |
| Các still/sequence khác được duyệt ở trên mặt nước | 37 |
| **Tổng** | **195** |

Các still đơn lẻ có source name khác nhau **không được coi là 27 camera hay 27 sự kiện độc lập được xác minh**. Metadata CC BY được giữ; upstream provenance vẫn có giới hạn. Bộ mới chứa nhiều cảnh instruction có caption và góc quay khác CCTV; chỉ dùng nhãn nguồn như proxy, không gọi đó là ca đuối nước lâm sàng đã được xác nhận.

Những phần bị loại lớn gồm camera underwater/half-water, cùng clip Thai news có vòng tròn chỉ target và đồ họa, stock/collage/film, tint/rotation, box head/body không nhất quán, nhãn drowning mâu thuẫn với frame bơi tương ứng và biến thể của resort validation. Ví dụ ID653/668 có source label drowning trong chuỗi bơi bình thường: loại ảnh, không tự sửa thành swimming. Các ảnh green-hall lesson được kiểm lại và loại nếu chưa xác lập được camera hoàn toàn ở trên nước.

## Nguyên tắc giữ tập đánh giá

- Canonical class **0=`drowning`, 1=`swimming`**. Nhãn chỉ có `out_of_water` có thể là ảnh background rỗng sau review; ảnh trộn class ngoài taxonomy không bị bỏ riêng box để giữ ảnh.
- Mọi ảnh bổ sung được duyệt phải là **train-only**. Cảnh `high_pool`, `indoor_pool`, `outdoor_resort_pool`, `competition_pool_cctv`, `indoor_other_cctv` bị khóa ngoài train. Các tên IMG_22xx/23xx được nhận ra là cùng resort validation và bị loại khỏi supplement.
- Validation/test v3 giữ đúng ảnh và nhãn; các alternate export không trở thành tập đánh giá mới. Dataset/khóa đánh giá legacy `deeprescue_v1` cũng giữ nguyên.
- Gộp các clip liên quan của bài học bơi vào group nguồn bảo thủ, gồm các góc quay cùng pool. Chỉ giữ đoạn camera **ở trên mặt nước**; camera underwater hoặc half-water/split-level bị loại, dù nhìn thấy người trên nước.
- Không dùng cảnh Thai news đã có vòng tròn chỉ target hoặc stock/collage/film để tăng số. Các caption tổng quát trong footage instruction được ghi là khác miền CCTV; không gọi dữ liệu trình diễn này là ca đuối nước được xác nhận độc lập.
- Audit kiểm ảnh decode, box, SHA-256, dHash và group qua split. 195 ảnh mới so với 1.118 ảnh v3 và 71 ảnh đánh giá legacy tạo **231.855 cặp**: không có dHash Hamming ≤4. Toàn bộ 1.007 train so với các val/test hiện tại và legacy tạo **379.639 cặp**: cũng không có match ở ngưỡng này. Năm frame supplement gần trùng đã loại là 225/274/347/348/353; supplement cuối không còn cặp Hamming ≤4. Kết quả ở `data/reviews/expanded_v4_overlap_audit.json`.
- Ngưỡng dHash chỉ là sàng lọc. Nó không chứng minh mọi crop, camera hoặc nguồn upstream độc lập; những frame gần nhau trong các group train cũ vẫn không phải tai nạn độc lập.

## Trạng thái đóng bộ

**Bộ surface_v4 đã đóng và audit đạt.** CSV `data/reviews/surface_v4.csv` có 1.313 record được duyệt; `data/curated/surface_v4/manifest.json` chứa ảnh/nhãn/hash/group được đưa vào train thật. `audit.json` có `build_completed=true`, `errors=[]`, không có exact duplicate cần bỏ trong bước build. `source_metadata.frozen_v3_validation_test_signatures_equal=true` xác nhận **từng ảnh + nhãn + split + group validation/test đúng v3**, không chỉ trùng số lượng. Không đánh giá test để chọn bộ dữ liệu hoặc hyperparameter.

Bằng chứng bổ sung:

- `data/reviews/expanded_v4_summary.json`: counts cuối và nguồn/group.
- `data/reviews/expanded_v4_decisions.json`: toàn bộ quyết định cuối, gồm second-pass và dedup.
- `data/reviews/expanded_v4_root_review.json`, `expanded_v4_frontend_review.json`: review riêng trước merge.
- `data/curated/surface_v4/attribution/alanoud/`, `attribution/mibugi/`: README/license/YAML gốc được giữ nguyên byte cùng source URL.
- `scripts/build_expanded_dataset.py`: quét phần chưa được whitelist, render, ghép và khóa đánh giá. Script đã chạy thành công end-to-end và kiểm tra cú pháp.

Lệnh đã dùng để tạo phiên bản này; script sẽ từ chối nếu chạy lại vào cùng output đã tồn tại:

```powershell
.venv\Scripts\python.exe scripts/build_expanded_dataset.py build --version surface_v4
```

Script từ chối ghi đè phiên bản cũ, từ chối chưa review xong hoặc ảnh mới đi vào val/test, giữ ảnh/nhãn đã review theo hash, rồi gọi `audit_dataset.py` để xuất manifest và cấu hình thật. Không chỉnh dataset sau audit trong lúc model train.

Huấn luyện do agent chính quản lý. Lần tiếp theo có thể tiếp tục từ **v3 BEST** với lineage/hash rõ vì v3 không từng train trên những cảnh val/test này. Phải ghi là continuation trên dữ liệu mới, giữ nguyên source annotation và chọn candidate bằng validation. Không cộng hai lịch epoch thành một run liên tục, không tự công bố hiệu quả trước khi đo và không lấy mAP bài báo làm kết quả hệ thống.
