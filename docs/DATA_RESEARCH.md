# Khảo sát dữ liệu, mô hình và hệ thống tương tự

Ngày kiểm tra: **28/10/2026**. Phạm vi là video quan sát **từ trên mặt nước**. Trang web, metadata/API, cây tệp, nội dung mã và archive được phân biệt rõ. Số lượng do chủ nguồn công bố không thay thế việc đếm và kiểm tra ảnh. Không dùng kết quả của bài báo làm kết quả của AquaWatch.

## 1. Bảy nguồn bắt buộc

### Loại tài nguyên và khả năng truy cập

| Nguồn | Loại, quy mô và nhãn | Tải, giấy phép, mô hình/mã |
|---|---|---|
| [1. Roboflow search](https://universe.roboflow.com/search?q=class%3Adrowning) | Trang tìm kiếm nhiều dataset, không phải một dataset. Có các dự án được khảo sát riêng ở bảng tiếp theo. | Export/version và quyền dùng phụ thuộc từng dự án. API minh họa trên trang không chứng minh có checkpoint tải local. |
| [2. Alanoud Awaji / Kaggle](https://www.kaggle.com/datasets/alanoudawaji/swimming-and-drowning-dataset) | **Đã tải** 388.922.012 byte: 9.997 ảnh, 9.997 YOLOv8 labels; 3 lớp Drowning/Swimming/out of water, 18.506 box; train/valid/test 6.014/1.977/2.006. Không có video/weights. | Kaggle ghi Unknown nhưng **README.dataset.txt và YAML ghi CC BY 4.0**, dẫn tới [Roboflow Alanoud version 4](https://universe.roboflow.com/alanoud/swimming-and-drowning-1jtbi). Trang gốc cũng xác nhận CC BY 4.0. Có thể ưu tiên tuyển chọn training; xem `FOLLOWUP_SOURCE_AUDIT.md`. |
| [3. Figshare](https://figshare.com/articles/dataset/Underwater_Drowning_Detection_Dataset/29497235/2) | Version 2: chủ nguồn công bố 5.613 ảnh 640×640; Swimming/Struggling/Drowning, mỗi lớp 1.871; JPEG + YOLO TXT; split 4.488/1.125. | CC BY 4.0; ZIP 1.600.698.646 byte có URL công khai. Chỉ đọc metadata, **không tải ảnh**. Không có checkpoint được xác minh. |
| [4. randhana / GitHub](https://github.com/randhana/Drowning-Detection-) | Repository, có video MP4, `model.pth`, `lb.pkl`, cấu hình YOLOv3; mã person detector + CNN và nhánh nhiều người dùng khoảng cách tâm. | MIT cho mã; quyền gốc video chưa rõ. `draw_bbox` tạo thread phát MP3 khi báo động. Chưa chạy repo cũ; tương thích dependency hiện tại chưa xác minh. |
| [5. Sensors 25(17), 5552](https://www.mdpi.com/1424-8220/25/17/5552) | Bài báo YOLO11-LiB: LGCBlock, C2PSAiSCSA, BiFF-Net. Công bố 2.000 ảnh gốc, tăng cường thành 4.800; train300 epoch. Kiểm tra bổ sung ZIP trong repo tác giả xác nhận **2.000 ảnh +2.000 nhãn YOLO**, split1.400/400/200, Drowning/Swimming. | [Mibugi/Drowning-detection](https://github.com/Mibugi/Drowning-detection) có ZIP101.111.276 byte và `LiB-YOLO.pt`, `yolo11n.pt`. **README/YAML trong dataset ghi CC BY4.0**; root repo chưa có LICENSE nên quyền custom code/weights cần xác minh riêng. Lần khảo sát đầu chưa đọc đủ metadata bên trong ZIP. |
| [6. nweweq / Roboflow](https://universe.roboflow.com/nweweq/drowning-detection-rawzc-y0qr2) | Trang hiện **264 ảnh**, 2 lớp drowning/swimming; **0 dataset versions, 0 models**. | CC BY 4.0. Có ảnh duyệt; chưa có version export được xác minh. Widget API tổng quát không phải model đã train của dự án này. |
| [7. Intelligent eyes on water](https://link.springer.com/article/10.1007/s11227-025-07732-7) | Bài báo YOLO11, Raspberry Pi 5, tracking; công bố 1.519 ảnh sau xử lý, nhãn Drowning/Normal; 120 epoch; dataset Hydrosavex. | Dataset dẫn tới [Roboflow app](https://app.roboflow.com/hydrosavex/hydrosavex-dataset/3/images). Weights công khai chưa xác minh. Bài báo open access; không đồng nghĩa dữ liệu được phép dùng mọi mục đích. |

### Độ phù hợp, chất lượng và quyết định

| Nguồn | Góc quay / underwater / CCTV | Chuỗi thời gian, annotation và trùng lặp | Quyết định |
|---|---|---|---|
| 1 | Từng dataset phải xem ảnh; không suy từ từ khóa drowning. | Nhiều bộ ảnh/frame; chưa chứng minh video gốc, nhãn sự kiện hoặc tính độc lập giữa các bộ. | Dùng để tìm ứng viên; không gộp số ảnh các kho thành số mẫu độc lập. |
| 2 | Đã xem 130 mẫu và box: có CCTV above-water, underwater/half-water, stock và biến thể xoay/đổi màu. | 1.433 tên gốc qua nhiều split; mẫu perceptual hash xác nhận chia sẻ phần lớn imagery với Deep Rescue. Nhãn ảnh yếu, không có event labels. | **Ưu tiên tuyển chọn mở rộng từ nguồn đã cung cấp**, loại mẫu không phù hợp, tái split theo nguồn; không gộp như nguồn độc lập hoặc train nguyên archive. |
| 3 | Chủ nguồn xác nhận **toàn bộ là ảnh từ camera underwater**, pool kiểm soát. | Có box YOLO; chưa audit box trực tiếp; ảnh không thay video temporal. Mức trùng lặp chưa đo. | **Loại toàn bộ dữ liệu**; chỉ tham khảo taxonomy và cách đánh giá. |
| 4 | Góc quay video chưa kiểm duyệt; không mặc định above-water. | Dùng khoảng cách <50 pixel của nhiều người để gán nguy hiểm là yếu, không thể suy ra cứu hộ/an toàn. Chưa có benchmark độc lập. | Tham khảo luồng cảnh báo, không nhập video/weights trực tiếp. |
| 5 | Bài báo và mẫu ZIP kiểm tra bổ sung đều có **above-water và underwater**. Có các cảnh trên mặt nước có thể tuyển chọn; không loại cả nguồn chỉ vì trộn góc nhìn. | YOLO box ảnh, không có temporal labels. ZIP README ghi không augmentation lúc export; bài báo có quy trình tăng cường riêng, không đồng nhất ZIP2.000 với4.800 ảnh trong bài. Metrics tác giả không áp cho ứng dụng. | **Ưu tiên tuyển chọn phần trên mặt nước để train**, giữ attributionCC BY4.0, loại underwater/không rõ quyền và chia lại theo video/camera; kiểm tra overlap với Alanoud/DeepRescue. Chưa train trên nguồn này trong lượt kiểm tra bổ sung. |
| 6 | Chưa kiểm duyệt 264 ảnh nên view/underwater/CCTV chưa xác minh. | Chất lượng box, nguồn gốc frame, temporal labels và trùng nguồn chưa xác minh. | Nguồn bổ sung để khảo sát, không chọn train/MVP vì thiếu version tải. |
| 7 | §5.1 xác nhận camera **underwater** trong pool. | Thiết kế temporal + ngưỡng 14 giây và local alarm/Firebase mobile. Phân chia ảnh không chứng minh độc lập video; mAP50 tác giả không dùng cho dự án. | **Loại dữ liệu underwater**; tham khảo event tracking và tách inference/báo động. |

## 2. Các ứng viên Roboflow đã mở riêng

Các số sau là số trang niêm yết, không phải số ảnh đã tải. Định dạng export và download có thể yêu cầu tài khoản/API key; chưa dùng tài khoản hoặc quota trả phí.

| Dataset | Quan sát trên trang | License / khả năng / hạn chế |
|---|---|---|
| [DrowningDetectionTracking](https://universe.roboflow.com/drowningdetection-2zzxz/drowningdetectiontracking) | 9.532 ảnh gốc, 2 version, 1 model; drowning / Out of Water / swimming. Version model ghi 23.562 ảnh, gồm xử lý/augmentation nên không cộng với ảnh gốc. | CC BY 4.0; YOLOv8s upload. View và nguồn video chưa audit. Số đo Roboflow không phải số đo của AquaWatch. |
| [Swimming and Drowning Detection / University](https://universe.roboflow.com/university-g3h71/swimming-and-drowning-detection) | 7.295 ảnh, 1 version, 1 model; Drowning / Person out of water / Swimming. | CC BY 4.0. Có trang version; chưa tải archive hoặc xác minh camera/box/duplicate. |
| [SwimmingXDrowning / Saharat](https://universe.roboflow.com/saharat-yyrhu/swimmingxdrowning) | Trang công khai/model được mở; search niêm yết khoảng 2.000 ảnh, 3 model, Drowning/Swimming. | Chưa xác minh license và version tải trong lượt này. Không chọn chỉ từ search snippet. |
| [Drowning datection / UAEU](https://universe.roboflow.com/uaeu-fkjhs/drowning-datection) | Trang dự án và version 1 được mở; search niêm yết khoảng 6.130 ảnh, drowning/swimming. | Chưa tải/audit; chưa xác minh toàn bộ license, quan hệ với các tập khác. |

## 3. Mở rộng tìm kiếm và kiểm tra archive thật

| Nguồn | Kết quả đã kiểm tra | Quyết định hiện tại |
|---|---|---|
| [Deep Rescue / Kaggle](https://www.kaggle.com/datasets/deeprescue/drowning-dataset) | **Đã tải** ZIP 219.926.172 byte. Đếm 9.990 JPG/JPEG và COCO JSON, 18.465 box. Nhãn Drowning, Person out of water, Swimming, underwater_swimmers (Humans là supercategory). Kaggle khai CC0, nhưng trường license trong COCO ghi Unknown. Có frame CCTV trên mặt nước, cảnh underwater và stock watermark. | Nguồn ứng viên để tuyển chọn thủ công; không dùng toàn bộ. Giấy phép do uploader khai chưa xác minh quyền tác giả từng ảnh. Cần lưu nguyên bản và khai báo giới hạn này. |
| [nvbangg / Kaggle](https://www.kaggle.com/datasets/nvbangg/drowning-test) | **Đã tải** ZIP 42.519.810 byte: 3 MP4 tên theo YouTube ID; metadata khai MIT. Không có bbox/temporal labels. | Không tự coi MIT uploader là giấy phép gốc YouTube. Chưa xác minh view/camera/nội dung/nguồn ban đầu; tạm ngoài benchmark chính. |
| [bhushankumarkashyap / Kaggle](https://www.kaggle.com/datasets/bhushankumarkashyap/drowning) | **Đã tải** ZIP 49.486.629 byte: 3.877 ảnh cropped theo thư mục; không có bbox YOLO. Metadata khai Apache-2.0. | Chưa kiểm duyệt view, taxonomy và nguồn ảnh; không chọn cho detector hiện tại. Không có weights trong archive. |
| [Z5cc/drowning-detection](https://github.com/Z5cc/drowning-detection) | Tác giả mô tả video snippets, nhãn CVAT và nguồn YouTube. | Hữu ích để thiết kế nhãn temporal/group theo video. Quyền video gốc chưa xác minh nên chưa nhập dữ liệu. |
| [Bagsangbin / Hugging Face](https://huggingface.co/Bagsangbin/yolo8s-drowning-detection/tree/main) | Đã tải checkpoint revision cố định và kiểm SHA-256, metadata AGPL-3.0. | Chỉ baseline cộng đồng. Chưa xác minh camera training, nguồn/split và video overlap. Yêu cầu tự fine-tune cần checkpoint mới cùng logs thực tế. Xem `ASSETS.md`. |
| [lonlonago dataset](https://github.com/lonlonago/Swimming-Drowning-Detection-Dataset) | Chủ trang yêu cầu trả tiền để nhận bộ đầy đủ. | Loại do yêu cầu miễn phí. Không xem preview như dataset tải đủ. |

Ảnh contact sheet **đã xem**: `data/research/deeprescue_groups.jpg`. Đây là mẫu đại diện theo prefix video, không phải giấy xác nhận mọi ảnh trong prefix. Nhiều prefix drowning1/20/47/50–55, Clipchamp/12 có cùng bể waterpark; phải gộp cùng nguồn/cảnh. Các prefix `video_2022-12-07_23-08-*` có cùng góc pool khác, cũng cần gộp. Các tên iStock/watermark, cảnh dưới nước, half-submerged camera và ảnh không xác định được camera phải loại khỏi tập duyệt. **Một người chìm nhìn từ trên mặt nước vẫn hợp lệ; camera dưới nước mới bị loại.**

## 4. Chiến lược dữ liệu và tự huấn luyện

Đây là phương án đề xuất; số mẫu được chấp nhận, logs huấn luyện và metrics thực phải lấy từ artifact pipeline sau khi chạy.

1. Lưu archive gốc và SHA-256; lập manifest cho từng ảnh gồm nguồn, tên gốc, clip/camera/session group, góc camera, quyết định giữ/loại, lý do và người/tiến trình duyệt. Không chép frame không rõ vào tập accepted.
2. Chọn các frame above-water đã kiểm trực tiếp và box hợp lệ từ nguồn có metadata license được ghi lại. Với Deep Rescue, nêu rõ license uploader CC0 và COCO Unknown; cần xác minh quyền ảnh gốc trước khi phát hành dataset. Loại toàn bộ iStock/watermark/underwater/không xác định.
3. Chuẩn hóa detector thành `drowning` (dấu hiệu hình ảnh nghi ngờ) và `swimming`; loại class underwater_swimmers và background/poolside nếu chưa có định nghĩa nhất quán. Không gán nhãn “đang được cứu/an toàn” chỉ vì đứng gần.
4. Khử byte duplicate, ảnh gần trùng và các augmentation của cùng frame. Nhóm theo video gốc/camera/session trước split; các frame liên tiếp và các góc của cùng sự cố đi cùng một split. Nếu không truy ra nhóm, loại hoặc gộp bảo thủ; không gọi split ảnh ngẫu nhiên là độc lập.
5. Thí nghiệm hiện tại fine-tune YOLOv8s từ **checkpoint drowning cộng đồng** đã ghim revision/SHA, để tận dụng class mapping và có baseline thực chạy trên máy. Đây là lựa chọn thực dụng để kiểm tra quy trình; dữ liệu upstream của checkpoint chưa công bố nên split local không chứng minh độc lập với pretraining. Cần bổ sung thí nghiệm khởi tạo COCO tổng quát để so sánh sau khi mở rộng dữ liệu. Lưu seed, phiên bản, tham số, SHA checkpoint đầu/cuối và `results.csv`; chỉ gọi hoàn tất sau khi log/weights/record xác nhận thành công. Tập nhỏ, ít epoch chỉ là thử nghiệm kỹ thuật, chưa chứng minh chất lượng.
6. Giữ nguyên val để chọn checkpoint/threshold; test không dùng chọn cấu hình. Nếu chỉ có hai nguồn/camera đã duyệt thì chưa đủ train/val/test độc lập: ghi thiếu dữ liệu, không chia cùng clip để tạo đủ ba nhãn split.
7. Đánh giá detection bằng box GT; đánh giá alarm bằng nhãn onset/end sự kiện + đối tượng. Báo precision/recall/F1, FP/hour, miss/event và độ trễ riêng. So sánh detector đơn frame với temporal filtering trên cùng tập khóa. Không dùng synthetic input làm bằng chứng độ chính xác thực tế.
8. Sau MVP, tăng các negative khó: lặn chủ động, giơ tay chào, nằm nổi, splash, người cứu hộ, che khuất và PTZ. Dữ liệu điện thoại được phép training nhưng test CCTV/PTZ phải báo riêng; không mặc định gộp dữ liệu luôn cải thiện.

**Dataset thử nghiệm hiện tại:** 192 ảnh Deep Rescue được duyệt theo whitelist, chia 121 train / 43 validation / 28 test theo ba nhóm cảnh `waterpark_main`, `high_pool`, `indoor_pool`; có manifest/audit trong `data/curated/deeprescue_v1/`. Nhãn gốc vẫn là nhãn yếu, chưa được kiểm chứng về tình trạng đuối nước; license gốc từng footage chưa đầy đủ. Đây chưa phải dataset học thuật cuối cùng. **Bổ sung:** Roboflow CC-BY sau khi tải và kiểm tra. **Không dùng:** Figshare underwater, Hydrosavex underwater, các mẫu underwater từ bất kỳ nguồn nào. **Test ngoài training:** footage công khai có license rõ và nguồn/video tách hẳn; chưa tuyên bố checkpoint cộng đồng chưa thấy video nào.

## 5. Video kiểm tra ngoài dataset

[USBP Rescues Drowning Man](https://www.dvidshub.net/video/812817/usbp-rescues-drowning-man) đã tải từ URL MP4 trong HTML DVIDS. Trang ghi PUBLIC DOMAIN, quay 01/09/2021; khoảng 1:45, 1024×576. Cần kiểm trực tiếp mọi đoạn trước khi chọn: loại cut/ảnh camera di chuyển tự do khỏi benchmark triển khai, giữ trên mặt nước. Có thể dùng thử luồng upload/inference, nhưng chưa có GT bbox/onset đầy đủ và chưa chứng minh không nằm trong training checkpoint cộng đồng. Không lấy nhãn tiêu đề làm GT từng frame.

[Drowning in 60 Seconds PSA](https://www.dvidshub.net/video/522681/drowning-60-seconds) bị loại khỏi tải/demo nguyên bản: [storyboard chính thức](https://corpslakes.erdc.dren.mil/employees/watersafety/pdfs/LJWNM%20Campaign%20Media%20Kit.pdf) có cảnh underwater và flashback. Video YouTube/phóng sự không có giấy phép phù hợp chỉ là đường dẫn khảo sát; chưa tự tải và không tính vào nghiệm thu.

## 6. Hệ thống thương mại và bài học thiết kế

Thông tin dưới đây là **nhà cung cấp công bố**, không phải kiểm định độc lập của dự án.

| Hệ thống | Kiến trúc/chức năng đã có nguồn | Bài học áp dụng và giới hạn |
|---|---|---|
| [Lynxight](https://www.lynxight.com/content/do-you-need-underwater-cameras-for-drowning-detection) | Overhead security cameras, AI theo dõi người, snapshot/vị trí gửi smartwatch/workstation; dùng nhiều góc để giảm che khuất. | Phù hợp hướng trên mặt nước. Áp dụng ID theo dõi, vị trí/vùng, thời gian và snapshot. Thuật toán/weights proprietary; không thể sao chép độ chính xác hoặc giả định một camera tương đương phủ nhiều góc. |
| [AngelEye](https://angeleye.tech/en/en-technology/) | Mô tả cả underwater và aerial camera, tracking, xác định vị trí, smartwatch/control screen/siren/light signals. | Áp dụng quy trình detect–event–evidence–operator. Đây là hệ thống có cấu hình nhiều camera; không diễn giải mọi hiệu năng của hãng thành khả năng above-water-only. |
| [SwimEye](https://swimeye.com/wp-content/uploads/2018/02/SwimEye_english_web_V2.pdf) | Tài liệu hãng mô tả underwater camera truyền về trạm phân tích và báo động. | Tham khảo luồng cảnh báo/trạm kiểm soát. Cấu hình này nằm ngoài phạm vi camera của bài tập; không lấy làm chứng cứ cho detector trên mặt nước. |

Đề xuất của AquaWatch: bốn trạng thái theo bằng chứng thời gian; có hysteresis/cooldown, snapshot, xác nhận riêng với tắt tiếng. Thay đổi góc/cắt cảnh làm gián đoạn bằng chứng theo dõi, không xác nhận chìm. Camera motion estimation chỉ là guard thận trọng; cần tập test PTZ gán nhãn trước khi tuyên bố hỗ trợ đáng tin cậy. Nhận diện cứu hộ thực sự, độ sâu, dòng chảy và mất ý thức cần nhãn/mô hình riêng; hiện chưa có căn cứ để tự kết luận.

## 7. So sánh AI và tài nguyên

| Hướng | Lợi ích dự kiến | Điều kiện/chưa chứng minh |
|---|---|---|
| Detector nhỏ + tracking + temporal state | Dễ chạy local, box + thời điểm rõ, dễ đo ablation. | Box/nhãn một frame chưa hiểu drowning. Cần GT video để chỉnh ngưỡng và đo latency. |
| Pose + chuỗi keypoint | Có thể bổ sung tư thế và nhịp cử động. | Người nhỏ/che khuất/nước phản chiếu làm keypoint yếu; không thay ground truth. Chưa train/chạy trong khảo sát này. |
| Video action model / temporal localization | Học diễn biến nhiều frame, phù hợp onset/end. | Cần clips có nhãn, GPU/memory và số sự cố độc lập lớn hơn. Chưa đủ dữ liệu đã duyệt để chọn làm MVP. |
| Full local | Không phí/quota, giữ dữ liệu tại máy. RTX 2060 6 GB do root kiểm thực tế. | Benchmark và batch/imgsz phải đo sau cài đặt; không dự báo số epoch/phút như kết quả thật. |
| Local + Kaggle/Colab | Có thể train lớn hơn rồi tải model về local. | GPU miễn phí phụ thuộc quota/tài khoản/tình trạng. [Colab FAQ](https://research.google.com/colaboratory/faq.html) nói tài nguyên không bảo đảm và giới hạn thay đổi; không cam kết số giờ GPU cố định. Không phụ thuộc cloud để demo. |
| Pretrained + fine-tune local | Thực hiện được yêu cầu tự huấn luyện và giảm nhu cầu dữ liệu/compute. | Phải giữ baseline và test nguồn tách biệt; không mặc định fine-tuned tốt hơn trước khi so sánh. |

Khuyến nghị: detector nhỏ fine-tune local trên tập đã duyệt, tracking/time evidence và web local. Dữ liệu temporal mở rộng và PTZ là các cổng nghiệm thu riêng. Cần nguồn/camera mới trước khi đánh giá đa môi trường pool/biển/sông/lũ; không suy rộng từ vài cảnh pool.
