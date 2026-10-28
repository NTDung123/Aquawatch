# Kiểm tra bổ sung nguồn 5 và nguồn 4

Ngày kiểm tra: 28/10/2026. Phạm vi: kiểm tra kho tác giả, metadata ZIP, giấy phép nhúng và mẫu ảnh; **không train lại và không thay dữ liệu/model đang dùng**.

## Kết luận cần cập nhật

Nguồn 5 **có dataset tải được, có khai báo giấy phép dataset và có checkpoint công khai**. Nhận xét trước đây “chưa xác minh checkpoint hoặc giấy phép dataset riêng” là trạng thái khảo sát còn thiếu, không phải bằng chứng những tài nguyên này không tồn tại. Việc loại sớm nguồn này chỉ vì chưa đọc được trang Roboflow là chưa đủ căn cứ.

Tuy nhiên dataset trộn camera trên/dưới nước, có ảnh stock có watermark và nhóm tên video xuất hiện qua các split. Cần lọc và chia lại trước khi dùng; kết quả khảo sát mẫu dưới đây chưa phê duyệt toàn bộ 2.000 ảnh.

## 1. Nguồn 5: dữ liệu thực trong kho tác giả bài Sensors

Bài báo [A Pool Drowning Detection Model Based on Improved YOLO](https://www.mdpi.com/1424-8220/25/17/5552) dẫn kho [Mibugi/Drowning-detection](https://github.com/Mibugi/Drowning-detection) trong Data Availability Statement; có [bản toàn văn PMC](https://pmc.ncbi.nlm.nih.gov/articles/PMC12431139/).

Đã đọc cây tệp GitHub đầy đủ, `truncated=false`, tại commit `a417d924b9d906dc50ab3078dd48b0c5c63a0f1c`.

| Tài nguyên xác minh | Kết quả |
| --- | --- |
| Dataset | `datasets/Drowning Detect.v6-2000.yolov11.zip`, **101.111.276 byte**, Git blob SHA `48ff50d2f5d9cf9fab7d08dee68d377d4848bc4b` |
| Số tệp ảnh thực theo central directory ZIP | **2.000**: train **1.400**, valid **400**, test **200** |
| Annotation | **2.000** tệp `.txt` trong `labels`; YOLO detection |
| Classes trong `data.yaml` | `nc: 2`; ID 0=`Drowning`, ID 1=`Swimming` |
| License dataset nhúng | `README.dataset.txt`: **CC BY 4.0**; `data.yaml` cũng ghi **CC BY 4.0** |
| Nguồn Roboflow nhúng | workspace `drowing-detect`, project `drowning-detect-fvwia`, version **6** |
| Xử lý được README export mô tả | Export 12/05/2025 07:47 GMT; auto-orientation; resize 640×640 kiểu stretch; **không augmentation trong bản export này** |
| Checkpoints có thật trong cây kho | `Module/LiB-YOLO.pt`: **4.464.654 byte**; `Module/yolo11n.pt`: **5.613.764 byte** |
| Mã công khai | YAML kiến trúc; `AddModules` với LAE, iSCSA, FreqFusion, BiFPN, DynamicConv; `train.py`, `predict.py`, `val.py` |
| License kho gốc | GitHub API ghi `license: null`, không có LICENSE cấp kho trong cây đã đọc. Một số file nguồn như `Module/train.py`, `predict.py` có header **AGPL-3.0 của Ultralytics**. Không suy ra dataset thiếu license từ việc kho không có LICENSE |

URL tải ZIP công khai, ghim commit:

[Drowning Detect v6, 2.000 ảnh, YOLOv11 ZIP](https://raw.githubusercontent.com/Mibugi/Drowning-detection/a417d924b9d906dc50ab3078dd48b0c5c63a0f1c/datasets/Drowning%20Detect.v6-2000.yolov11.zip)

[Trang phiên bản Roboflow được ghi trong archive](https://universe.roboflow.com/drowing-detect/drowning-detect-fvwia/dataset/6)

GitHub connector đọc được metadata/mã nhưng không tải binary. Đã dùng HTTP Range đọc central directory, ba tệp README/YAML và 41 mẫu ảnh/nhãn từ URL raw; **chưa tải toàn bộ ZIP và chưa giải mã kiểm tra đủ 2.000 ảnh**. Số lượng trên là đếm entry trong archive thực, không suy đoán từ tên ZIP.

Giấy phép công bố trong bản export tạo căn cứ sử dụng kèm attribution, nhưng chưa xác minh được quyền của người phát hành với mọi ảnh/video bên thứ ba. Quan sát watermark stock bên dưới là lý do phải thẩm tra/lọc riêng những mẫu đó, không phải lý do phủ nhận việc archive đã khai báo CC BY 4.0.

## 2. Quan sát trực tiếp trên 41 mẫu

Chọn mẫu theo các nhóm tên video phổ biến, một số nguồn có tên gợi ý stock/phim và ảnh tên số. Đã xem cả bốn contact sheet kèm box. Đây là mẫu phân tầng để phát hiện vấn đề, **không phải lấy mẫu ngẫu nhiên để ước lượng tỷ lệ chất lượng**.

| Quan sát | Bằng chứng mẫu | Ý nghĩa |
| --- | --- | --- |
| Có camera trên mặt nước | Mẫu #1–3, #5, #9: `IMG_3607_MOV` đến `IMG_3611_MOV`; #6 `IMG_20240627`; #11/#20/#22/#24 pool góc cao; #37–40 pool CCTV xa | Có phần dữ liệu tiềm năng cho dự án, cần duyệt toàn bộ phần giữ |
| Có camera đặt dưới nước | Mẫu #0 `14_mp4`; #4 `9_mp4`; #8 `17_mp4`; #10 `18_mp4`; #14 `19_mp4`; #15/#17 `1_mp4`/`2_mp4`; #18/#19 `13_mp4`/`15_mp4`; #27 `drowning_001_mp4`; #28 `notdrowning_mp4`; #32 `both2_mp4` | Những mẫu này phải loại khỏi mọi split theo yêu cầu người dùng; đây là góc camera dưới nước, không chỉ là nạn nhân chìm nhìn từ bờ |
| Có ảnh stock mang watermark | #26/#30/#31/#34 có watermark iStock/Getty; một số tên file cũng ghi nguồn stock | Cần loại hoặc kiểm tra quyền riêng của tài nguyên; license metadata chung chưa xác minh quyền nguồn gốc của từng ảnh |
| Có frame phim | #25 tên `Jennifer-Lawrence-drowning-Passengers-Movie` | Không mặc định là footage CCTV hoặc video sự cố thật |
| Có nghi vấn video liên quan nguồn 4 | Tên gốc `drowning_001`, `notdrowning`, `both2` xuất hiện trong archive; source 4 có video trùng tên; mẫu #27/#28/#32 là camera dưới nước | Cần đối chiếu nguồn/ảnh trước khi gộp; không coi hai kho là dữ liệu độc lập chỉ vì khác URL |
| Có cảnh đã thấy trong DeepRescue | Các nhóm `video_2022-12-07_23-08-*` có cùng pool/góc cao quan sát được trong subset DeepRescue hiện tại | Không đưa nhóm này vào train bổ sung rồi giữ chúng làm test độc lập. Cần kiểm tra hash/perceptual hash đầy đủ trước khi kết hợp |

Filename audit cho thấy **66 nhóm stem có ít nhất ba ảnh xuất hiện ở nhiều split**. Ví dụ:

- `14_mp4`: train 98, valid 31, test 13.
- `IMG_3607_MOV`: train 81, valid 25, test 5.
- `video_2022-12-07_23-08-12_mp4`: train 30, valid 5, test 5.

Đây là bằng chứng **nguy cơ rò rỉ theo video gốc qua tên file**, chưa phải chứng minh mọi cặp là ảnh trùng pixel. Không nên dùng nguyên split 7:2:1 đã xuất để công bố khả năng tổng quát hóa CCTV. Cần gộp thêm các clip cùng pool/camera/phiên rồi chia lại theo nhóm trước huấn luyện.

Bài báo mô tả 2.000 ảnh gốc và tập mở rộng 4.800 ảnh, trộn góc trên và dưới nước. Archive gốc 2.000 ảnh được kiểm tra ở đây ghi không augmentation; không được nói đã tải bản mở rộng 4.800 ảnh khi chưa có bản đó. Metrics do tác giả công bố không phải kết quả của AquaWatch.

## 3. Nguồn 4: repo randhana có model và video, nhưng provenance chưa đủ

Đã đọc [README](https://github.com/randhana/Drowning-Detection-/blob/master/README.md), [LICENSE](https://github.com/randhana/Drowning-Detection-/blob/master/LICENSE), [DrownDetect.py](https://github.com/randhana/Drowning-Detection-/blob/master/DrownDetect.py), [cvlib/object_detection.py](https://github.com/randhana/Drowning-Detection-/blob/master/cvlib/object_detection.py), requirements và cây tệp đầy đủ tại commit `3ec16b99f16e377901c1bb65193e378f299e9d2c`.

- LICENSE cấp kho là **MIT**, copyright Pulathisi Kariyawasam, 2023. Có thể tham khảo/tái sử dụng phần mềm theo điều kiện giấy phép; phải giữ attribution theo license.
- `model.pth` có thật, **1.088.235 byte**; `lb.pkl` **492 byte**. Code định nghĩa một `CustomCNN`, đọc label binarizer, load state dict và phân loại khung hình thành `drowning`/`normal` theo nhãn được code tham chiếu.
- Có **12 tệp MP4**, tổng **114.469.505 byte**, gồm `both2.mp4`, `drowning_001.mp4`, `notdrowning.mp4` và ba clip trong `videos/test/`.
- README tuyên bố model học trên nhiều ảnh/video nhưng **không dẫn dataset huấn luyện, manifest, bản quyền/attribution từng video, split, code train hoặc model card**. Cây tệp đã đọc cũng không có thư mục ảnh/annotation train đầy đủ. Không có bằng chứng đủ để xác nhận nguồn dữ liệu train của `model.pth` hoặc quyền nguồn gốc của từng MP4.
- MIT của phần mềm không tự xác minh quyền của người phát hành với mọi footage bên thứ ba. Cách diễn đạt đúng là **“repo có MIT, nhưng provenance/quyền từng media và dữ liệu model chưa được tài liệu hóa đầy đủ”**, thay vì “repo không có license” hoặc “không có model/video”.

Về thuật toán, code dùng YOLOv3 tải trọng số object detector chung từ pjreddie; nếu có một box thì CNN phân loại **toàn frame**; nếu nhiều box thì đặt cảnh báo theo khoảng cách tâm nhỏ hơn **50 pixel**. Không thấy lịch sử track/mô hình hành động theo thời gian trong đoạn logic chính. Các box chưa được lọc chỉ còn người trước nhánh đếm số lượng; một biến cảnh báo chung được truyền cho phần vẽ. Alarm tạo thread khi vẽ box cảnh báo, chưa thấy cooldown sự kiện. Vì vậy mô tả README về “motion analysis/tracking” chưa được hiện thực đầy đủ trong đoạn code đã kiểm tra.

Không chạy code của repo và không tải/load `model.pth` trong đợt kiểm tra này. Mục tiêu là xác minh tài nguyên/provenance, không tuyên bố repo hoạt động tương thích hoặc đạt độ chính xác.

## 4. Khuyến nghị cụ thể

Nguồn 5 nên được giữ trong danh sách **ứng viên dữ liệu huấn luyện trực tiếp sau sàng lọc**, thay vì chỉ xem là bài báo tham khảo. Bước kế tiếp hợp lý là tải archive gốc CC BY 4.0, lưu attribution, duyệt/loại camera dưới nước và ảnh có vấn đề quyền nguồn, audit box/nhãn, đối chiếu trùng với nguồn 2/DeepRescue/nguồn 4, rồi chia lại theo video/scene. Chưa thực hiện các bước này đủ toàn bộ nên chưa chốt nó là dataset cuối.

Nguồn 4 phù hợp tham khảo code/cảnh báo và khảo sát video có nguồn; chưa đủ làm dataset train độc lập chỉ vì có MIT và video mẫu. Các clip trùng nhóm camera dưới nước phải bị loại theo yêu cầu, bất kể giấy phép.

## 5. Bằng chứng local

Tất cả bằng chứng lần khảo sát này ở `D:\httm\.work\source5\`:

- `mibugi_tree.json`, `randhana_tree.json`, metadata API kho và các file README/LICENSE/code đã đọc.
- `zip_entries.json`: toàn bộ entry ZIP, compressed/uncompressed size và local offset.
- `README.dataset.txt`, `README.roboflow.txt`, `data.yaml`: nội dung thật giải nén từ remote ranges.
- `inspection.json`: danh sách 41 mẫu kèm SHA-256, nhãn và các nhóm tên file qua nhiều split.
- `source5_samples_0.jpg` đến `_3.jpg` và `samples/`: ảnh/annotation mẫu đã xem.
- `inspect_remote_zip.py`: tái hiện tải mẫu qua HTTP Range trên commit đã ghim.

Không có file nào từ lần khảo sát này được đưa vào `data/curated`, `data/training` hoặc `models`.
