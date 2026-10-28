# Kết quả kiểm thử và phần chưa đạt

Ngày thực hiện: **28/10/2026, giờ Việt Nam**. Mọi số dưới đây lấy từ artifact trên máy; không lấy số của bài báo/nhà cung cấp làm kết quả dự án.

## 1. Tự fine-tune đã thực hiện

Run hoàn tất: `data/training/finetune_v2/training_record.json`, `results.csv`, `args.yaml`, `weights/best.pt`, `weights/last.pt`. Tám epoch thực, ảnh 416, batch 4, seed42, RTX2060, PyTorch2.7.1+cu126; AMP tắt để tránh tải checkpoint phụ cho phép kiểm tra AMP. Có logs loss và cập nhật optimizer; không chỉ đổi tên trọng số.

- Dữ liệu gốc Deep Rescue: 9.990 ảnh, 18.465 COCO boxes; không dùng cả bộ.
- Đã xem 225 candidate kèm box; loại33, giữ192 ảnh trên mặt nước.
- Split theo ba cảnh: train121 `waterpark_main`, validation43 `high_pool`, test28 `indoor_pool`. Chỉ có ba scene group; không coi192 ảnh là192 tình huống độc lập.
- Manifest, quyết định giữ/loại, contact sheets, SHA và audit nằm trong `data/reviews/`, `data/curated/deeprescue_v1/`.
- Checkpoint gốc SHA `6e8094468fa0294887a930bf18db9e7c5989a74d5e3c1753ec21c4d742e72c29`.
- Checkpoint fine-tune SHA `3fac4df1920833be69c211d4089441abf5dbb78fd1cf68553a3229599a0e6861`; được nạp thật vào API, có hash trong kết quả job.

Lượt `finetune_v1` thất bại do Windows pipe bị sandbox chặn; giữ nguyên record lỗi. Lượt `v2` chạy được ngoài sandbox, mọi output vẫn trong dự án. Không tính lượt lỗi là huấn luyện thành công.

## 2. So sánh detector bằng số đo thật

Đánh giá baseline/candidate cùng cấu hình imgsz416, batch4, confidence0,001, NMS IoU0,7, FP32. Validation được dùng chọn checkpoint. Sau đó đánh giá test một lần bằng `evaluate_detector.py`; không lấy test chọn lại tham số. Các giá trị P/R là thống kê detector do Ultralytics báo ở chế độ đánh giá, không phải P/R sự kiện của ứng dụng với ngưỡng0,4.

| Split | Model | Precision | Recall | mAP50 | mAP50–95 |
|---|---|---:|---:|---:|---:|
| Validation43 ảnh | Baseline cộng đồng | 29,21% | 56,58% | 20,42% | 8,82% |
| Validation43 ảnh | Fine-tune8 epoch | 49,62% | 71,05% | 47,91% | 22,52% |
| Test28 ảnh, cảnh khác | Baseline cộng đồng | 10,84% | 10,74% | 3,33% | 0,76% |
| Test28 ảnh, cảnh khác | Fine-tune8 epoch | 20,59% | 14,13% | 6,72% | 2,06% |

Nguồn số: `data/evaluation/val_v1/comparison.json`, `data/evaluation/test_v1/comparison.json`; có metrics theo lớp, confusion matrix và các plot trong thư mục con. Test lớp drowning của candidate: precision15,92%, recall25,93%, mAP50 6,74%. **Kết quả này thấp, chưa đạt chất lượng cảnh báo đáng tin cậy.** Cải thiện validation không chứng minh tổng quát hóa tốt. Không đổi mAP thành “độ chính xác phát hiện đuối nước”.

Các split chỉ giữ ngoài **lần fine-tune này**. Không biết checkpoint cộng đồng trước đó đã thấy ảnh/video nào, nên chưa chứng minh độc lập với toàn bộ pretraining. Audit còn hai nhóm có cùng dHash bên trong test; không có dHash bằng nhau qua split, nhưng chưa loại hết tương quan giữa các frame cùng cảnh. Nhãn drowning/swimming lấy từ nguồn, một số frame/box không đủ xác nhận hành vi; có nhãn thiếu hoặc box nhóm người. Giấy phép uploader CC0 và COCO Unknown chưa giải quyết quyền footage gốc. Các yếu tố này giới hạn giá trị của metrics.

## 3. Chạy toàn luồng qua HTTP với video thật

Video USBP/DVIDS dài105,6055 giây, 1024×576, 29,97FPS; kiểm tra contact sheets mỗi2 giây trên toàn thời lượng cho thấy cảnh từ bờ/trên mặt nước, có zoom/pan. Đây là footage cứu hộ công khai dùng smoke test; không phải benchmark CCTV tĩnh đã xác minh độc lập. Không có GT box/onset/end do người gán nhãn cho toàn bộ video, không suy GT từ tiêu đề.

| Lượt | Baseline đầu tiên | Fine-tune trên bản mã cuối |
|---|---:|---:|
| Job | `82de634003054c088e225cbd4618ffca` | `b0ff7384ccc9456dabe0d8b9fb827d18` |
| Thời gian xử lý | 22,032 giây | 22,655 giây |
| Samples | 528 | 528 |
| Detections dự đoán | 74 | 200 |
| Đoạn cảnh báo dự đoán | 21 | 28 |
| Mức tối đa | 2 | 3 |
| Mean inference | 29,84ms | 30,58ms |
| Throughput mẫu phân tích | 23,96FPS | 23,31FPS |

Hai lượt khác cả checkpoint và một số bản vá logic, nên **không dùng bảng này làm ablation chứng minh fine-tune cải thiện cảnh báo**. Lượt đầu dẫn tới bản vá gộp hụt detector, giữ trạng thái mất dấu chưa xác minh, khóa job và báo đúng checkpoint. Số events không phải số sự cố thật; không khẳng định28 cảnh báo đúng. Mean bị ảnh hưởng warmup nên có thể cao hơn p95.

`data/baseline_live_smoke.json`, `data/finetuned_live_smoke.json` chứng minh upload201 → job202 → completed → analysis200 → JSON/CSV200 → ack200 → ảnh bằng chứng200. Lượt fine-tune xuất JSON215.348 byte, CSV3.602 byte, ảnh bằng chứng đầu63.556 byte. Kiểm tra cuối: `/api/status` báo fine_tuned=true, reload_pending=false; static assets200; video byte range206/1.024 byte để hỗ trợ tua. Chưa đo event precision/recall/F1, FP/giờ, false negatives hay độ trễ từ onset thật.

Đã xem một số ảnh bằng chứng: detector có thể bao cả nhóm người trong một box. Không khẳng định tracking nhận dạng từng nạn nhân chính xác. Những trường hợp đang được cứu vẫn có thể báo nguy cơ; proximity không tự chứng minh an toàn.

## 4. Kiểm thử mã

Lệnh thực chạy: `.venv/Scripts/python.exe -m pytest -q -p no:cacheprovider --basetemp .work/pytest-final` → **33 passed, 1 warning**. Warning là deprecation của Starlette TestClient/httpx, không phải lỗi ứng dụng trong bộ kiểm thử.

Phạm vi:19 ca API;8 ca risk/mất dấu/camera/hysteresis;2 ca phép đo sự kiện;4 ca bảo vệ audit/split dữ liệu. Kiểm thử logic dùng dữ liệu giả lập có kiểm soát, **không được tính làm bằng chứng độ chính xác AI trên video thật**. `node --check web/app.js` đạt; parser PowerShell không báo lỗi cho SETUP/RUN. Không chạy lại cài đặt từ máy sạch nên không khẳng định đã kiểm thử clean install.

## 5. Trạng thái nghiệm thu

| Hạng mục | Kết quả |
|---|---|
| Đọc4 deck/khảo sát7 nguồn và môi trường | Có trích xuất, bảng nguồn, phân loại và hạn chế |
| Tự fine-tune | Đã chạy thực, có checkpoint/log/config/audit |
| Upload video mới → AI thật → lưu kết quả | Đạt qua HTTP với footage thật |
| Overlay, play/pause/seek, review, banner, âm/rung | Có mã và kiểm tra logic; **chưa nghiệm thu bằng trình duyệt thực** |
| Lịch sử, evidence, ack, export | API đã xác minh; thao tác UI chưa kiểm tra trực tiếp |
| Chất lượng detector cảnh mới | **Chưa đạt**; test mAP50 chỉ6,72% trên tập nhỏ/nhãn yếu |
| Sự kiện temporal độc lập/CCTV âm tính | **Thiếu dữ liệu và GT hợp lệ**; có evaluator nhưng chưa có kết quả thực |
| Camera PTZ | Có guard chuyển động, reset track/ROI; chưa benchmark PTZ/compensation hoàn chỉnh |
| Điện thoại, LAN, loa, rung, Notifications | **Chưa kiểm tra thiết bị thật** |
| Tất cả dữ liệu fine-tune trên mặt nước | 192 ảnh đã duyệt; pretraining checkpoint chưa truy được góc quay |
| Quyền nguồn ảnh/độc lập upstream | Chưa xác minh đầy đủ; không phát hành dataset như đã bảo đảm quyền |

Công cụ UI trả `apps:[]`, `browsers:[]`, lỗi `Computer Use native pipe is unavailable`. Do đó không có screenshot giao diện hoặc bằng chứng nghe loa/rung điện thoại từ phiên này. HTTP200 và kiểm thử source không thay thế các bước đó.

## 6. Việc cần làm tiếp theo theo mức ảnh hưởng

1. Thu thập/được cấp dữ liệu CCTV có quyền rõ, nhiều camera và sự cố/negative khó; gán nhãn bởi người có hiểu biết hành vi. Giữ nguồn mới hoàn toàn làm test khóa, vì test hiện đã được xem kết quả.
2. Mở rộng train/validation theo nguồn, loại near-duplicate/augmentation trước split; thử generic COCO init và so sánh cùng protocol để giảm bất định về pretraining.
3. Gán nhãn temporal onset/end/track và trạng thái không quan sát được; hiệu chỉnh ngưỡng theo recall/FP/hour; so sánh temporal và detector riêng. Không dùng tập test hiện tại để chọn ngưỡng rồi gọi nó độc lập.
4. Kiểm tra bằng trình duyệt Windows và điện thoại thật: tọa độ/letterbox, không có tương lai, pause/seek, âm opt-in/mute/ack, codec/LAN/notification. Chuẩn hóa video về MP4 H.264 nếu cần.
5. Chỉ bổ sung pose/action/rescue-context/multi-camera sau khi có dữ liệu và tiêu chí đánh giá. Hiện chưa có cơ sở xác nhận mọi hành vi hoặc mọi môi trường nước.
