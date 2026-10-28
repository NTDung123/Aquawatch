# Kiểm tra bổ sung các nguồn người dùng đã cung cấp

Ngày kiểm tra: 28/10/2026. Tài liệu này bổ sung việc kiểm tra **nội dung tải về**, thay cho kết luận chỉ dựa trên metadata trang tổng quan. Không chạy huấn luyện mới trong lần kiểm tra này; giữ nguyên dataset/test đã khóa.

## Nguồn 2 — Swimming and Drowning Dataset của Alanoud Awaji

### Kết luận được sửa

Nguồn người dùng cung cấp **có archive miễn phí tải được, ảnh và nhãn YOLOv8 để huấn luyện**. Kết luận trước đây tạm loại vì Kaggle ghi `Unknown` là chưa đầy đủ: bên trong archive, **`README.dataset.txt` và `data.yaml` cùng ghi CC BY 4.0**, dẫn tới [dự án Alanoud trên Roboflow](https://universe.roboflow.com/alanoud/swimming-and-drowning-1jtbi), trang này cũng xác nhận CC BY 4.0. Không cần yêu cầu người dùng tìm nguồn huấn luyện khác trước khi khai thác nguồn đã cung cấp.

Giấy phép đã được xác minh ở mức **dataset do người đăng phát hành**; nguồn gốc/quyền từng footage vẫn cần lưu lại khi tuyển chọn. Mẫu có watermark iStock không nên tự coi được chủ dataset cấp quyền lại. Đây là lý do lọc mẫu cụ thể, không phải lý do phủ nhận toàn bộ tiềm năng của bộ dữ liệu.

### Tải và đếm nội dung thực tế

| Hạng mục | Kết quả đã kiểm tra |
|---|---|
| Nguồn | [Kaggle Alanoud Awaji](https://www.kaggle.com/datasets/alanoudawaji/swimming-and-drowning-dataset) |
| Archive local | `data/research/alanoud.zip` |
| Tải công khai | `https://www.kaggle.com/api/v1/datasets/download/alanoudawaji/swimming-and-drowning-dataset` |
| Dung lượng / SHA-256 | 388.922.012 byte / `54b20dcb7c85c9bf717938e7a5f61c81fbd75ec0af35ffbcc93891ca1bd9f9b1` |
| Version nguồn | Kaggle version 2; export gốc Roboflow **version 4**, 23/05/2024. Hai version thuộc hai nền tảng khác nhau. |
| Số tệp | 19.997 entries; **9.997 ảnh + 9.997 tệp nhãn** + 3 metadata |
| Split có sẵn | Train 6.014 ảnh; valid 1.977; test 2.006 |
| Class ID từ YAML | `0 Drowning`, `1 Swimming`, `2 out of water` |
| Số box | Drowning **10.699**; Swimming **7.195**; out of water **612**; tổng **18.506** |
| Kiểm tra nhãn dạng số | Không có tệp nhãn rỗng; không phát hiện dòng sai 5 trường, class không đọc được hoặc tọa độ chuẩn hóa ngoài [0,1]/kích thước không dương. Kiểm tra cú pháp không chứng minh nhãn đúng nghĩa. |
| Chuỗi thời gian | **Không có video** trong archive. Tên ảnh có frame `_mp4`, `_MOV`; không có temporal event labels hoặc track ID được xác minh. |
| Chênh lệch số lượng | README và trang Roboflow nêu 9.999 ảnh; archive tải thực tế có **9.997**, dùng số đếm thực khi báo cáo. |
| Trọng số | Không có weights trong archive; trang dự án Roboflow hiện ghi 0 model. Đây là nguồn dữ liệu, không phải checkpoint sẵn. |

Tái hiện phần tải/đếm/đọc metadata: `python scripts/inspect_alanoud.py`. Kết quả máy đọc: `data/research/alanoud_audit.json`.

### Quan sát ảnh và bounding box

Đã xem **130 ảnh mẫu**, chọn đầu/giữa/cuối theo prefix video và 30 ảnh ngẫu nhiên seed 42; xem cả ảnh gốc và overlay box. Contact sheets: `data/research/alanoud_samples_1.jpg` đến `_4.jpg`, `alanoud_boxes_1.jpg` đến `_4.jpg`. Đây không phải kiểm duyệt đủ 9.997 ảnh.

- Có nhiều ảnh camera **trên mặt nước**, góc cao nhìn xuống bể, phù hợp làm ứng viên training sau review; xuất hiện các cảnh waterpark, pool nhìn cao và CCTV indoor.
- Có ảnh camera **dưới nước**, ảnh chia đôi trên/dưới mặt nước, collage và stock watermark. Phải loại chúng theo yêu cầu, không dùng nguyên archive.
- Đã có ảnh xoay, biến màu và chèn/ghép vùng ảnh. README nói không áp augmentation khi export; điều đó **không chứng minh dữ liệu nhập ban đầu chưa được augmentation**.
- Nhiều box định vị người rõ, nhưng có box rất nhỏ, crop cơ thể, collage và nhãn hành vi chỉ từ ảnh. Cần kiểm tra bỏ sót/nhãn sai theo định nghĩa tác vụ; không xem class Drowning là xác nhận y khoa.
- Dữ liệu không có lớp underwater riêng vẫn có thể chứa góc quay dưới nước. **Không được chỉ lọc theo tên class** rồi coi mọi ảnh còn lại là above-water.

### Trùng lặp với Deep Rescue và rủi ro split

Đã so sánh ảnh trong hai archive; không thay đổi train/validation/test đang dùng. Kết quả lưu ở `alanoud_deeprescue_overlap.json` và `alanoud_overlap_perceptual_sample.json` trong `data/research/`.

| Phép kiểm tra | Kết quả | Diễn giải |
|---|---|---|
| SHA-256 byte ảnh giải nén | 0 hash chung giữa hai kho | Không chứng minh ảnh độc lập: hai export có resize/recompression khác nhau. |
| Tên ảnh gốc chuẩn hóa | **1.778 tên chung**; Alanoud có 1.790 tên gốc chuẩn hóa, Deep Rescue 2.067 | Bỏ hậu tố `.rf.<hash>`, phần mở rộng và `_jpg/_png`; tên trùng riêng lẻ chưa đủ chứng minh cùng ảnh. |
| Ảnh có tên gốc khớp | **9.969/9.997 Alanoud**, **9.653/9.990 Deep Rescue** | Phần lớn hai archive có quan hệ nguồn rất gần. Không cộng tổng thành ~20.000 mẫu độc lập. |
| Mẫu perceptual dHash theo tên chung | 256 tên, seed 42: **235 khớp dHash tuyệt đối**, **254 có Hamming distance ≤4** khi so biến thể phù hợp nhất | Cùng các cảnh quan sát trực tiếp, đây là bằng chứng mạnh hai kho chia sẻ phần lớn imagery. dHash là kiểm tra hỗ trợ, có thể va chạm và chưa phải đối chiếu toàn bộ video. |
| Trùng byte nội bộ Alanoud | 9.898 hash ảnh khác nhau trong 9.997 ảnh: **99 bản dư trùng byte**; không có hash giống hệt băng qua split | Vẫn cần khử near-duplicate và nhóm nguồn; hash byte khác không ngăn leakage. |
| Tên gốc qua split Alanoud | **1.433 tên gốc** xuất hiện trong nhiều split | Split có sẵn có rủi ro rò rỉ frame/biến thể cùng nguồn. Prefix video cũng phân bố nhiều split. Không dùng nguyên split để tuyên bố tổng quát hóa. |

**Nhận định:** Alanoud rất gần Deep Rescue về dữ liệu gốc, có class mapping/định dạng/resize khác; chưa đủ căn cứ gọi hai kho giống hệt hoặc Alanoud chỉ đơn giản là Deep Rescue bỏ class underwater. Hai tập có số ảnh và tập tên gốc khác nhau. Chắc chắn không nên gộp chúng như hai nguồn độc lập.

### Ý nghĩa cho lần huấn luyện tiếp theo

Nguồn đã cung cấp có tiềm năng lớn hơn nhiều so với tập thử **192 ảnh** trước đó. 192 ảnh là whitelist đã duyệt cho một thí nghiệm nhỏ, **không phải toàn bộ khả năng khai thác các nguồn người dùng đưa**.

Bước tiếp theo hợp lý là ưu tiên Alanoud version 4 làm nguồn ảnh/YOLO có CC BY 4.0 để tuyển chọn mở rộng: giữ above-water, loại underwater/stock/ảnh không rõ, chuẩn hóa hai/ba lớp theo mục tiêu, bỏ biến thể trùng và gom theo video/camera/session. Các cảnh đã nằm trong validation/test khóa của thí nghiệm trước phải tiếp tục được cách ly khi xây dựng dataset phiên bản mới; không đưa bản export khác của chúng vào train. Cần manifest mới và chỉ huấn luyện sau khi hoàn tất review/split. Kiểm thử độ chính xác sự kiện vẫn cần video có nhãn theo thời gian; tập ảnh này chưa thay thế phần đó.
