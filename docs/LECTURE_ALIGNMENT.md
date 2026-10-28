# Đối chiếu bài giảng và yêu cầu AquaWatch

Ngày kiểm tra: 28/10/2026. Nguồn chính là bốn tệp PowerPoint do người dùng chỉ định. Đây là phân tích tài liệu học phần và yêu cầu sản phẩm, không phải một bảng tiêu chí chấm điểm do giảng viên ban hành.

## 1. Kết quả đọc tài liệu

| Tệp nguồn | Số slide | Nội dung đã xác minh | Ảnh nhúng trong slide | Notes có nội dung |
| --- | ---: | --- | ---: | ---: |
| [Lecture1.pptx](C:/Users/tuand/Desktop/Lecture1.pptx) | 32 | Nhập môn machine learning; classification, regression, clustering; supervised/unsupervised learning; NumPy; khoảng cách, tìm kiếm và phân cụm | 8 | 0 |
| [Lecture2.pptx](C:/Users/tuand/Desktop/Lecture2.pptx) | 29 | Matplotlib; scikit-learn; quy trình load/preprocess/split/train/evaluate/predict; OpenCV; ảnh và video | 10 | 0 |
| [Lecture3.pptx](C:/Users/tuand/Desktop/Lecture3.pptx) | 29 | Linear regression, loss và gradient descent; KNN, chuẩn hóa đặc trưng; K-means | 12 | 0 |
| [Lecture4.pptx](C:/Users/tuand/Desktop/Lecture4.pptx) | 30 | AI/ML/DL; representation learning; neural network, activation, forward/backpropagation; train/test; overfitting, regularization; CNN/RNN/Transformer | 18 | 0 |

Đã trích xuất văn bản của toàn bộ **120 slide**, giữ số thứ tự theo danh sách slide trong `ppt/presentation.xml`, đồng thời kiểm tra trực quan **48 ảnh nhúng**. Các ảnh chủ yếu minh họa đồ thị, ma trận, KNN/K-means, cấu trúc mạng, tensor, hàm kích hoạt và quy trình huấn luyện; không phát hiện yêu cầu riêng của đề tài đuối nước trong những ảnh này.

Nội dung bốn deck tập trung vào **học máy và học sâu**. Không có tên chính thức “Hệ thống thông tin” hoặc “Hệ thống thông minh” trên trang tiêu đề để xác nhận tên học phần. Vì vậy dự án giữ tên môn theo yêu cầu người dùng, đồng thời đối chiếu đúng nội dung ML thực tế. Bốn deck này không cung cấp bài giảng UML, mô hình cơ sở dữ liệu, use case, ERD, kiến trúc phần mềm hay thang điểm riêng cho đề tài đuối nước. Những thiết kế này có thể phục vụ chất lượng sản phẩm và yêu cầu người dùng, nhưng không được viện dẫn thành yêu cầu bắt buộc từ slide.

### Tái hiện việc đọc nguồn

```powershell
python scripts/extract_lectures.py
```

Lệnh mặc định đọc `Lecture1.pptx` đến `Lecture4.pptx` trên Desktop và tạo:

- [lectures_extracted.txt](lectures_extracted.txt): toàn bộ đoạn văn bản và token công thức theo thứ tự nguồn.
- [lectures_extracted.json](lectures_extracted.json): văn bản theo slide, notes, danh mục ảnh và công thức OMML nguyên gốc; có SHA-256 của từng PPTX.

Có thể truyền bốn đường dẫn đầu vào khác. Khi cần đối chiếu ảnh gốc:

```powershell
python scripts/extract_lectures.py --media-dir .work/lecture_media
```

Văn bản thuần không bảo toàn ký hiệu phân số/căn/chỉ số của công thức. JSON giữ XML OMML để không đánh mất cấu trúc gốc. File PPTX gốc là nguồn quyết định khi cách biểu diễn công thức thuần văn bản gây mơ hồ. Script không thay đổi các tệp nguồn.

## 2. Phân biệt ba nguồn yêu cầu

### A. Tình huống của giảng viên do người dùng thuật lại

Theo văn bản yêu cầu của người dùng, tình huống tối thiểu là: xuất hiện người cầu cứu ở bể bơi/bờ biển; phần mềm phát hiện, đánh dấu đối tượng, thông báo và cảnh báo. Người dùng cũng cho biết giảng viên kỳ vọng xét tình huống chìm dưới mặt nước và chưa bắt buộc kết nối camera vật lý.

Những thông tin này có nguồn là **lời mô tả của người dùng**. Không tìm thấy chúng trong bốn slide, nên không mô tả là điều đã được kiểm chứng độc lập từ đề bài/rubric chính thức.

**Làm rõ bổ sung trong phiên làm việc:** người dùng xác nhận giảng viên **bắt buộc tự train hoặc fine-tune**. Vì vậy pretrained chỉ được dùng làm khởi tạo/baseline; bản nộp cần có một lần huấn luyện/fine-tuning thực, cấu hình và log/checkpoint có thể kiểm tra. Yêu cầu này có nguồn là thông tin làm rõ của người dùng, không phải suy ra từ bốn slide.

### B. Yêu cầu mở rộng do người dùng đặt ra

- Phân tích video đã ghi từ camera quan sát **trên mặt nước**; ưu tiên camera có vị trí cố định, hỗ trợ camera xoay theo khả năng đã kiểm thử.
- Dữ liệu huấn luyện được phép đa dạng, kể cả camera cầm tay trên bờ; dữ liệu triển khai/kiểm thử chính phải giống camera giám sát mục tiêu. Loại toàn bộ footage camera dưới nước ở cả train, validation, test và demo.
- Phân biệt dấu hiệu quan sát trực tiếp, suy luận theo thời gian và tình huống không đủ thông tin; không kết luận chìm chỉ vì mất dấu.
- Có mức cảnh báo dựa trên tiêu chí rõ ràng, ổn định theo thời gian, đồng bộ với thời gian video, có xác nhận/tắt âm có kiểm soát và lịch sử bằng chứng.
- Giao diện Windows thuận tiện, ưu tiên web dùng được trên điện thoại; không mua thiết bị hoặc dùng dịch vụ trả phí.
- Khảo sát đủ bảy nguồn dữ liệu/nghiên cứu, tìm thêm nguồn phù hợp; ghi giấy phép, nguồn gốc, khả năng tải và thông tin chưa xác minh.
- Đo hiệu năng thực; thiết kế đánh giá theo sự kiện và dữ liệu độc lập; không dùng mAP/accuracy của tác giả khác như kết quả dự án.
- Lưu toàn bộ mã nguồn, kết quả, cấu hình và hướng dẫn tái hiện trong `D:\httm`; không tạo kết quả AI giả.

### C. Kiến thức và bài tập thực sự xuất hiện trong slide

- Lecture1 slide 18, 25, 31 có các ví dụ khoảng cách vector, tìm tâm cụm và top-K search. Đây là bài tập thực hành NumPy, không phải yêu cầu dùng cả ba thuật toán trong sản phẩm đuối nước.
- Lecture2 slide 11 có ví dụ CIFAR-10, clustering, PCA và Matplotlib; slide 21 yêu cầu bài tập supervised classification trên CIFAR-10 với accuracy `>0.5`.
- Lecture3 slide 9–10, 18, 27 đưa ví dụ xây dựng linear regression, KNN và K-means “from scratch”.
- Lecture4 slide 13, 25, 27, 29 có ví dụ mạng nơ-ron tự xây dựng; slide 29 đặt accuracy CIFAR-10 `>0.6`.

Các ngưỡng **0.5 và 0.6 áp dụng cho những ví dụ CIFAR-10 được nêu**, không phải ngưỡng nghiệm thu phát hiện đuối nước. Bốn deck không đủ căn cứ để kết luận có yêu cầu huấn luyện YOLO riêng hay tự cài toàn bộ detector. Tuy nhiên, thông tin làm rõ của người dùng đã xác nhận yêu cầu **tự train/fine-tune**, nên quy trình dự án phải đáp ứng điều đó. Không suy rộng thành cấm dùng pretrained để khởi tạo khi chưa có quy định như vậy.

## 3. Bảng đối chiếu kiến thức, yêu cầu và thiết kế sản phẩm

Bảng này phân biệt kiến thức đã đọc và cách áp dụng trong dự án. Cột áp dụng là quyết định kỹ thuật của nhóm phát triển; việc đạt nghiệm thu phải dựa trên kiểm thử ứng dụng và kết quả đo, không dựa riêng vào bảng.

| Nguồn đã xác minh | Kiến thức thực tế | Yêu cầu liên quan | Cách áp dụng/kiểm chứng trong AquaWatch |
| --- | --- | --- | --- |
| Lecture1 slide 2–7, 10 | Học từ dữ liệu; classification; supervised learning cần dữ liệu có nhãn | Nhận diện dấu hiệu nguy hiểm bằng AI thực | Dùng checkpoint có nguồn; ghi đúng các lớp model dự đoán. Lớp tên `drowning` của bộ dữ liệu chỉ là nhãn đầu ra, không phải xác nhận y khoa |
| Lecture1 slide 8–9; Lecture3 slide 4–8, 20–26 | Phân biệt regression, classification và clustering | Chọn thuật toán đúng bài toán | Detection định vị và phân lớp dấu hiệu; state machine xử lý sự kiện. Không dùng clustering như nhãn nguy hiểm đã được xác minh; không ép linear regression vào video nếu không có mục tiêu liên tục phù hợp |
| Lecture1 slide 11–17, 20–24, 27–30 | NumPy, shape, indexing, slicing, reshape, phép toán, sao chép mảng | Xử lý frame và tọa độ bounding box | Xử lý frame bằng NumPy/OpenCV; chuẩn hóa tọa độ khi vẽ overlay; tránh sửa nhầm frame gốc qua tham chiếu mảng |
| Lecture1 slide 18, 31; Lecture3 slide 13, 16–17 | Khoảng cách, top-K, chuẩn hóa đặc trưng; hạn chế KNN với dữ liệu lớn | Theo dõi người và tránh nhầm đặc trưng | Có thể dùng khoảng cách/IoU khi ghép track; nếu thêm classifier đặc trưng thì fit scaler trên train. Khoảng cách giữa box chưa đủ chứng minh hai người là cùng một người hoặc đang cứu nhau |
| Lecture2 slide 2–10 | Biểu đồ đường/cột/scatter và nhiều biểu đồ | Báo cáo đo FPS, độ trễ, lỗi và mức cảnh báo | Xuất kết quả có thời gian và đơn vị; dựng biểu đồ từ kết quả thật khi có dữ liệu. Biểu đồ đẹp không thay cho ground truth |
| Lecture2 slide 14–19 | Scikit-learn; pipeline load/preprocess/split/train/evaluate/predict | Quy trình đánh giá tái hiện được | Lưu cấu hình model/dữ liệu và chia train/validation/test trước thử nghiệm; tách theo video/phiên ghi hình để tránh rò rỉ frame. Cách tách theo video là bổ sung theo đặc thù dự án, không phải câu nguyên văn trong slide |
| Lecture2 slide 17 | Scikit-learn có hạn chế với deep learning và GPU | Chọn thư viện phù hợp laptop GPU | Dùng PyTorch/Ultralytics cho detector; scikit-learn có thể phục vụ baseline/metrics, không thay engine GPU cho video |
| Lecture2 slide 24–27 | OpenCV: ảnh là ma trận, BGR; resize/crop; vẽ; video capture; tích hợp deep learning | Đọc video thật, khoanh đối tượng | Giải mã video, lấy timestamp, đưa frame vào detector, hiển thị box và nhãn; kiểm tra màu/kích thước và đồng bộ với playback |
| Lecture2 slide 28 | Perspective correction trong ví dụ quét tài liệu | Camera có góc quan sát khác nhau | Chỉ xem là kiến thức phép biến đổi hình học; không suy ra ví dụ này tự giải quyết PTZ hoặc đã hiệu chuẩn mặt nước |
| Lecture3 slide 6–7; Lecture4 slide 9–11, 21–23; thông tin làm rõ của người dùng | Loss, tối ưu và đánh giá prediction so với truth | Bắt buộc tự train/fine-tune theo thông tin người dùng | Fine-tune thực và lưu loss, cấu hình, checkpoint, manifest train/validation; pretrained chỉ là baseline/khởi tạo. Không coi thay threshold cảnh báo là đã huấn luyện mạng |
| Lecture3 slide 15–17 | KNN có thể overfit/underfit, phụ thuộc scale và nhiễu | So sánh baseline và tổng quát hóa | Có thể thiết kế baseline trên đặc trưng theo thời gian sau khi có nhãn. Không thêm KNN chỉ để có tên thuật toán học phần |
| Lecture4 slide 6–8, 16–21, 26 | Mạng học biểu diễn; layer, weights, activation, forward pass; chi phí/khả năng diễn giải | Giải thích kiến trúc AI và giới hạn | Trình bày detector là thành phần học sâu, tách rõ inference của mạng và quy tắc thời gian do nhóm viết; ghi độ tin cậy là score của model, chưa được hiệu chuẩn thành xác suất tai nạn |
| Lecture4 slide 13, 23–24, 29 | Train/test; quy trình huấn luyện; overfitting, dropout, regularization, early stopping | Kiểm thử video chưa dùng huấn luyện | Giữ tập test khóa riêng; chọn threshold trên validation; công bố riêng kết quả theo bể bơi/biển/sông và camera tĩnh/xoay khi đủ dữ liệu |
| Lecture4 slide 18, 24 | Tensor chuỗi thời gian, ảnh; CNN cho ảnh, RNN cho chuỗi | Người chìm/mất dấu cần thông tin theo thời gian | Lưu track history và chuỗi dấu hiệu; có thể mở rộng action model khi có video có nhãn. Detector từng frame cộng quy tắc thời gian không đồng nghĩa đã huấn luyện RNN/action recognition |
| Không có trong bốn deck; do người dùng yêu cầu | CSDL, quản lý sự kiện, xác nhận, UI, API, truy xuất nguồn gốc | Sản phẩm hoạt động và có thể trình diễn | Thiết kế riêng luồng video–AI–risk–event–UI, lưu bằng chứng/lịch sử và hướng dẫn chạy lại; ghi là yêu cầu sản phẩm, không gán cho nội dung slide |

## 4. Yêu cầu chức năng và tiêu chí kiểm chứng

| Mã | Yêu cầu | Tiêu chí kiểm chứng thực tế |
| --- | --- | --- |
| FR-01 | Nhập video trên mặt nước và khai báo bối cảnh | Chọn/tải một video mới; backend mở được file; lưu metadata nguồn/góc quay theo thông tin người dùng. Khai báo của người dùng cần được kiểm tra khi lập bộ đánh giá |
| FR-02 | Phân tích bằng mô hình thực | Kết quả có tên/nguồn/hash model, thời gian xử lý và detection từ inference; lỗi model phải hiển thị lỗi |
| FR-03 | Theo dõi và phân tích diễn biến | Có track/time của detection; xử lý mất dấu riêng với sự kiện đã quan sát; phát hiện scene cut/chuyển động camera phải làm giảm tin cậy suy luận mất dấu |
| FR-04 | Mức cảnh báo có lý do | Hiển thị bằng chứng và tiêu chí mức nguy hiểm; lưu threshold/cấu hình; kiểm thử nâng/hạ mức và cơ chế chống nhấp nháy |
| FR-05 | Đồng bộ thời gian video | Tua về trước/sau và tạm dừng không được phát cảnh báo của tương lai. Chế độ xử lý trước phải được ghi rõ |
| FR-06 | Khung đỏ và thông tin đối tượng | Box được đặt đúng hệ tọa độ video, nhãn/score dễ đọc; trạng thái mất dấu không vẽ box như detection hiện thời |
| FR-07 | Âm thanh và cảnh báo đa thiết bị | Có thao tác bật/test âm; phát theo quyền của trình duyệt; rung/notification dùng feature detection và phản hồi khi không hỗ trợ |
| FR-08 | Lịch sử và xác nhận | Có thể xem thời gian, đối tượng, mức, lý do, bằng chứng; xác nhận không tự xóa kết luận chưa an toàn hoặc gọi cứu hộ thật |
| FR-09 | Xem lại và xuất kết quả | Từ sự kiện nhảy tới đúng timestamp; xuất JSON/CSV hoặc báo cáo có nguồn/cấu hình |
| FR-10 | Không nhầm mất dấu do PTZ là chìm | Kiểm thử đoạn camera xoay và scene cut; không sinh kết luận xác nhận chìm chỉ do biến mất khỏi khung |
| FR-11 | Nghiên cứu và quản trị dữ liệu | Bảng khảo sát đủ bảy nguồn, góc quay, license, khả năng tải và trạng thái xác minh; các mẫu loại bỏ có lý do |
| FR-12 | Đánh giá độc lập | Có manifest video gốc/nguồn/nhãn, split theo nguồn và kết quả đo thật; nếu chưa có nhãn hoặc chưa rõ train provenance thì ghi “chưa xác minh độc lập” |
| FR-13 | Tự train/fine-tune theo làm rõ của người dùng | Có lệnh huấn luyện thật, log optimizer/loss, cấu hình, manifest dữ liệu, hash checkpoint đầu/cuối và kết quả validation. Smoke training ngắn phải ghi đúng tính chất, không tự xem là mô hình đạt chất lượng cuối |

### Yêu cầu phi chức năng

- **Tái hiện:** có hướng dẫn cài/chạy, dependency và cấu hình, nguồn và hash model; mọi kết quả trong `D:\httm`.
- **Hiệu năng:** đo thời gian đọc/AI/xử lý tổng, FPS và GPU thực tế; không đưa ra ngưỡng “real time” chung trước khi đo. Xử lý trước rồi phát lại vẫn hợp lệ theo yêu cầu người dùng nếu ghi đúng chế độ.
- **Độ tin cậy:** backend báo lỗi rõ ràng, không tự thay kết quả AI bằng dữ liệu minh họa; trạng thái không đủ quan sát phải hiện khác với bình thường.
- **Khả năng sử dụng:** kiểm tra trực tiếp luồng upload, xử lý, playback, tua, xác nhận và âm báo trên desktop; kiểm tra responsive bằng viewport hẹp và tách riêng kiểm thử trên điện thoại thật.
- **Nguồn gốc và bảo mật:** không ghi secrets vào mã nguồn; không tự gửi dữ liệu ra dịch vụ ngoài hoặc tự gọi số khẩn cấp; không mặc định camera trên mặt nước thấy được nạn nhân dưới nước đục.
- **Tính trung thực khoa học:** tách precision/recall/mAP của detection khỏi event recall, false alarms/hour và detection latency. Không tuyên bố thiết bị cứu sinh đã được chứng nhận.

## 5. Kiến thức nên giải thích khi bảo vệ

1. **Mô hình dự đoán điều gì?** Nêu chính xác các lớp trong checkpoint, dữ liệu huấn luyện được công bố đến đâu, và vì sao score đầu ra chưa phải xác suất một người đang đuối nước.
2. **Thuật toán do nhóm xây dựng là gì?** Giải thích ghép track, tích lũy dấu hiệu theo timestamp, state machine cảnh báo, xử lý mất dấu và hạn chế PTZ. Không gọi các quy tắc này là neural network đã huấn luyện.
3. **Vì sao không dùng mọi thuật toán trong slide?** KNN/K-means/linear regression là những phương án phải hiểu và so sánh; chọn thuật toán theo dữ liệu/mục tiêu, không ghép cho đủ danh sách.
4. **Đã tránh leakage ra sao?** Chia theo video gốc/phiên/camera, kiểm tra trùng giữa nguồn; không chia ngẫu nhiên các frame liền nhau rồi báo kết quả là video độc lập.
5. **Đã chứng minh được đến đâu?** Tách smoke test chạy pipeline khỏi đánh giá accuracy trên ground truth và kiểm thử tình huống thật. Nêu những môi trường chưa có dữ liệu kiểm chứng.
6. **Có phù hợp với nội dung học phần không?** Liên hệ NumPy/OpenCV, supervised learning, inference của mạng sâu, train/test và đánh giá bằng dữ liệu. Kiến trúc web/CSDL hỗ trợ việc hiện thực hóa sản phẩm, không được mô tả là nội dung đã có trong bốn deck.

## 6. Những điểm cần rubric ngoài bốn bài giảng

Người dùng đã làm rõ việc bắt buộc tự train/fine-tune. Những điểm vẫn chưa có bằng chứng là: số thuật toán phải tự cài; mẫu báo cáo, định dạng nộp, thang điểm; ngưỡng độ chính xác/độ trễ áp dụng cho đề tài; yêu cầu UML/ERD cụ thể. Các thông tin này không cản trở xây dựng MVP, nhưng cần bổ sung trước khi chốt bản nộp học phần nếu giảng viên có quy định riêng.

Một chi tiết cần đọc đúng: Lecture2 slide 19 có tiêu đề “Classification with linear regression” nhưng code dùng `LogisticRegression`. Khi giải thích học thuật nên căn cứ thuật toán thực trong code, không gọi logistic regression là linear regression chỉ vì tiêu đề nguồn.
