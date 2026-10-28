# Quy trình dữ liệu và tự fine-tune

Người dùng xác nhận giảng viên yêu cầu **tự train/fine-tune**. Chỉ thay threshold cảnh báo hoặc chạy inference bằng pretrained không đáp ứng yêu cầu đó. Hai script dưới đây hỗ trợ huấn luyện thật và ghi bằng chứng; sự tồn tại của script chưa chứng minh đã chạy huấn luyện.

## 1. Chuẩn bị dữ liệu có nguồn gốc

Giải nén bản YOLO detection có `images` và `labels` vào một thư mục nguồn trong `data/raw/`. Kiểm tra đúng thứ tự class ID từ `data.yaml` gốc. Không suy ra ID `drowning` từ tên thư mục hoặc tên model.

Tạo bảng duyệt:

```powershell
.venv\Scripts\python.exe scripts/audit_dataset.py init --source-root data/raw/nguon --review data/reviews/nguon.csv
```

Mọi dòng mặc định là `pending`, `viewpoint=unknown`. Script không tự xác nhận camera trên mặt nước. Người duyệt cần xem ảnh và bounding box, kiểm tra giấy phép/nguồn rồi điền:

| Cột | Giá trị và ý nghĩa |
| --- | --- |
| `review_status` | `approved` sau khi kiểm tra; `rejected` cho ảnh không dùng |
| `viewpoint` | Chỉ `above_water` được giữ; `underwater`/`unknown` bị loại |
| `camera_motion` | `fixed`, `ptz`, `handheld` hoặc `unknown`; ảnh tĩnh có thể không đủ xác định chuyển động camera |
| `source_group` | ID video gốc/phiên ghi hình hoặc nhóm nguồn có căn cứ. Toàn bộ frame gần nhau cùng một nhóm; không dùng tên ảnh riêng làm group để né kiểm tra |
| `split` | `train`, `val` hoặc `test`, gán ở mức source group |
| `source_url` | Trang nguồn thực, ưu tiên video/dataset gốc |
| `license` | Giấy phép đã kiểm tra và cho phép dùng; không điền “unknown” để phê duyệt |
| `notes` | Lý do chấp nhận/loại, sửa nhãn, nguồn video chưa rõ hoặc giới hạn annotation |

Nếu không biết video gốc, cần ghi rõ điều đó. Có thể làm một **thí nghiệm kỹ thuật thăm dò** trên dữ liệu được duyệt, nhưng không được gọi tập validation đó là kiểm thử CCTV độc lập. Để tuyên bố tổng quát hóa phải có bộ test camera phù hợp, không trùng nguồn, có nhãn thời gian và không dùng để tinh chỉnh.

## 2. Lọc, khử trùng và chia tập

Ví dụ sau chỉ đúng nếu `data.yaml` nguồn thực sự dùng class ID 0=`drowning`, 1=`swimming`:

```powershell
.venv\Scripts\python.exe scripts/audit_dataset.py build --source-root data/raw/nguon --review data/reviews/nguon.csv --output data/curated/v1 --classes drowning swimming
```

Script kiểm tra ảnh mở được, label YOLO có năm trường, class ID đúng, tọa độ hợp lệ, nguồn/giấy phép được khai báo, chỉ giữ ảnh `approved above_water`, không cho cùng `source_group` sang nhiều split. SHA-256 phát hiện ảnh trùng hoàn toàn; trùng ảnh nhưng khác nhãn hoặc khác split làm audit thất bại. dHash bằng nhau qua nhiều split cũng yêu cầu người duyệt xử lý. dHash không phát hiện mọi frame gần trùng, nên vẫn cần nhóm theo video và duyệt bằng mắt.

Đầu ra gồm `data.yaml`, `manifest.json`, `audit.json`, ảnh/nhãn được sao chép và danh sách loại bỏ trong audit. Dùng thư mục phiên bản mới mỗi lần; script không ghi đè dataset đã xây dựng. Nếu audit thất bại, file `<review>.audit_errors.json` ghi lỗi và chưa tạo dataset.

Khi gộp nguồn: thống nhất định nghĩa nhãn, class ID và định dạng trước; đối chiếu frame/video gốc và duplicate giữa các nguồn trước khi chia tập. Không cộng tổng ảnh rồi coi tất cả là mẫu độc lập. Không dùng dữ liệu camera đặt dưới nước cho bất cứ split nào.

## 3. Chạy một thí nghiệm fine-tuning thật

Checkpoint khởi tạo phải là tệp local có nguồn và quyền sử dụng rõ. Cấu hình ban đầu phù hợp để đo trên RTX 2060 6 GB là ảnh 640 và batch 4; nếu thiếu VRAM, giảm batch/ảnh sau khi ghi nhận lỗi. Không khẳng định thời gian hoặc chất lượng trước khi chạy.

```powershell
.venv\Scripts\python.exe scripts/train_detector.py --dataset data/curated/v1 --model models/base.pt --epochs 30 --imgsz 640 --batch 4 --device auto --name experiment_v1 --purpose experiment
```

Script dùng Ultralytics `model.train`, có forward/loss/backpropagation/optimizer thật; seed 42, workers 0 cho Windows, thư mục cache nằm trong dự án. `--purpose smoke` dùng cho kiểm tra ngắn, `experiment` dùng cho thử nghiệm, `final_candidate` chỉ thể hiện mục đích chạy và không tự chứng nhận mô hình đã đạt.

AMP mặc định tắt để tránh thư viện tải một model khác chỉ phục vụ phép kiểm tra AMP; dùng `--amp` nếu đã chủ động chuẩn bị điều kiện này. Windows sandbox có thể chặn named pipe nội bộ mà Ultralytics dùng khi quét label, kể cả `workers=0`; khi đó lần chạy phải được ghi là lỗi, rồi chạy lại trong môi trường được phép tạo pipe. Không sửa log lỗi thành thành công.

`data/training/<name>/` chứa cấu hình Ultralytics, `results.csv`, đồ thị khi thư viện tạo, `weights/best.pt`, `weights/last.pt`, và `training_record.json` với:

- Thời điểm bắt đầu/kết thúc, trạng thái thực và lỗi nếu có.
- Phiên bản Python, thư viện, GPU/CUDA, câu lệnh và seed.
- Hash checkpoint khởi tạo, checkpoint kết quả, audit và manifest dữ liệu.
- Metrics validation của chính lần chạy, tách khỏi metrics tác giả khác.

`best.pt` khác hash checkpoint gốc chỉ là bằng chứng tệp thay đổi. Cần xem log loss/optimizer và `results.csv` để kiểm tra huấn luyện thực. Không được dựa riêng hash để kết luận chất lượng tăng.

## 4. Đánh giá và chọn model

So sánh cùng tập validation đã khóa: pretrained baseline; fine-tune; fine-tune cộng temporal analysis. Không chọn threshold/epoch bằng tập test. Khi đã chốt phương án, có thể thêm `--evaluate-test` để đánh giá split test trong lần chạy có kiểm soát; không lặp để tối ưu trên test.

Để so sánh baseline và fine-tune cùng cấu hình, dùng:

```powershell
.venv\Scripts\python.exe scripts/evaluate_detector.py --dataset data/curated/deeprescue_v1 --baseline models/drowning_yolov8s.pt --candidate data/training/finetune_v2/weights/best.pt --split val --output data/evaluation/val_v1
```

Lệnh chỉ chạy sau khi checkpoint candidate thực sự đã được tạo. `comparison.json` lưu hash, metric tổng/theo lớp, thời gian đo và giới hạn. Khi đã chọn model, thay `--split test` và dùng thư mục đầu ra mới để đánh giá tập test khóa một lần; script ghi `test_evaluation_lock.json` sau một lần đánh giá test hoàn tất. Giữ kết quả và không tối ưu trên split này.

Metrics ảnh (precision, recall, mAP) không thay thế metrics sự kiện. Cần bộ video CCTV trên mặt nước độc lập với nhãn người/thời điểm và báo cáo event recall, false alarms/hour, detection latency, ID switches/fragmentation nếu có nhãn track; đo riêng camera tĩnh, PTZ và từng môi trường. Video smoke test chưa có nhãn hoặc chưa rõ dữ liệu pretrain không đủ để công bố accuracy.

Model fine-tune chỉ được đưa vào ứng dụng sau khi kiểm tra đúng class mapping, inference trên video thật, cảnh báo theo thời gian và kiểm thử hồi quy. Một lần smoke training ít epoch đáp ứng việc chạy quy trình huấn luyện kỹ thuật, nhưng chưa đủ căn cứ để coi là mô hình cuối có hiệu quả.

## 5. Bộ dữ liệu thí nghiệm đã chuẩn bị trong phiên này

`data/curated/deeprescue_v1/` đã được xây dựng từ archive Kaggle `deeprescue/drowning-dataset` có 9.990 ảnh. Đây là một **subset thăm dò**, không phải dataset hoàn chỉnh đã được xác thực hành vi:

- Đã duyệt trực quan 225 candidate kèm bounding boxes trên chín contact sheet `data/reviews/deeprescue_review_00.jpg` đến `_08.jpg`.
- Loại 33 candidate do lộn ngược/biến màu mạnh/nhiễu/khung khó diễn giải; giữ 192 ảnh được quan sát từ phía trên mặt nước, không có ảnh stock có watermark trong whitelist được chọn.
- Train: 121 ảnh thuộc nhóm bảo thủ `waterpark_main`; validation: 43 ảnh `high_pool`; test: 28 ảnh `indoor_pool`. Gộp những clip cùng scene trước khi chia, không chia ngẫu nhiên từng frame. Không có SHA-256 hoặc dHash bằng nhau qua split trong audit này.
- Giữ nhãn nguồn `Drowning` thành ID 0=`drowning`, `Swimming` thành ID 1=`swimming`. Chỉ duyệt tính hợp lý hình học ở độ phân giải nguồn; **chưa xác thực mọi nhãn hành vi**, có thể thiếu box hoặc nhãn sai. Một frame không đủ kết luận một người đang đuối nước.
- Kaggle uploader khai báo CC0-1.0, nhưng COCO ghi license `Unknown` và chưa xác minh được chủ sở hữu video gốc. Subset chỉ phục vụ thí nghiệm học thuật local trong phiên này; cần xác minh quyền nguồn gốc trước khi phân phối lại dữ liệu. Không tuyên bố có quyền không giới hạn với footage gốc.
- Chia scene chỉ bảo đảm tách đối với lần fine-tune này. Nếu khởi tạo bằng checkpoint drowning cộng đồng thì không chứng minh được các scene chưa có trong dữ liệu pretrained. Chưa đủ căn cứ gọi đây là bộ test độc lập hoàn toàn.

Quyết định từng candidate nằm trong `data/reviews/deeprescue_candidates.json`; ảnh/box gốc, source URL, class mapping, hash archive và các hạn chế nằm trong `data/raw/deeprescue_reviewed/source.json`, CSV review và `data/curated/deeprescue_v1/audit.json`. `scripts/prepare_training_subset.py` tái tạo YOLO subset từ archive và các quyết định đã duyệt. Các ảnh không thuộc whitelist bị loại khỏi subset; không gán toàn bộ 9.798 ảnh còn lại là camera dưới nước vì chưa duyệt hết chúng.
