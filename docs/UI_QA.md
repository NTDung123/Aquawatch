# Kiểm tra giao diện AquaWatch

Cập nhật kiểm thử logic ngày **12/11/2026**. Phạm vi: giao diện local trong `web/`, tự nhận diện video CCTV bể bơi có sẵn. Không kết nối camera vật lý.

## Luồng hiện tại và kiểm thử đã chạy

- `node --check web/app.js`: đạt.
- `node tests/frontend_timeline.test.cjs`: đạt; xác minh **80 liên kết phần tử HTML**.
- Chọn video bằng thư viện/dropdown tự gửi yêu cầu `realtime`, camera cố định, môi trường bể bơi và ngưỡng do model đang triển khai khuyến nghị. Không cần checkbox xác nhận, chọn mode hoặc bấm nút phân tích thứ hai. Các thiết lập/phân tích lại nằm trong phần nâng cao đóng mặc định.
- Tải tệp xong tự chạy nhận diện. API upload dùng `above_water=true` theo phạm vi người dùng đã yêu cầu: CCTV bể bơi trên mặt nước. Tệp lỗi hiển thị lỗi; không tạo kết quả giả.
- Đổi video khi phiên trước đang chạy vẫn được phép: giao diện gửi hủy, chờ trạng thái kết thúc rồi mới gửi phiên mới. Các thao tác được xếp hàng và chỉ lựa chọn mới nhất còn hiệu lực được chạy.
- Đã kiểm tra chọn liên tục, POST tạo job trả muộn và upload trả muộn. Job cũ tạo muộn được dừng trước phiên mới; upload cũ thành công vẫn được giữ nhưng không tự chạy nhầm video. Mở lịch sử chỉ phục hồi phiên đã lưu, không tạo job mới.
- Thư viện chính/dropdown chỉ hiển thị catalog đang hoạt động và video tải lên đang được chọn. Các upload smoke test cũ không tự xuất hiện trong thư viện CCTV mới; vẫn có thể mở qua lịch sử.
- Nếu `model.ready=false`, giao diện báo AI đang khởi động và chờ sẵn sàng. Phát nguồn được thử ngay trong thao tác chọn và mặc định tắt tiếng nguồn. AudioContext được chuẩn bị trong thao tác chọn/phát video; thanh trạng thái chỉ rõ đã sẵn sàng, do người dùng tắt hoặc bị trình duyệt chặn, kèm nút bật lại.
- Realtime polling mỗi 300 ms, tiếp tục phát khi có tối thiểu khoảng 0,3 giây kết quả. Video/tua bị chặn tại `processed_until`; hết kết quả thì chờ, có thêm dữ liệu chỉ tiếp tục nếu người dùng còn muốn phát. Phiên hủy giữ giới hạn phần đã xử lý.
- Không lấy sample tương lai, không giữ box quá lâu, không hiển thị ID sự kiện tương lai khi giám sát. Âm chỉ được đánh dấu đã phát sau khi lên lịch oscillator thành công; có nhắc lại giới hạn 8 giây khi cảnh báo còn hoạt động. Bật lại âm, khôi phục AudioContext hoặc tăng âm lượng từ 0 có thể báo lại sự kiện hiện tại; pause, tương lai, sample cũ và sự kiện đã xem không phát âm.
- Mock AudioContext kiểm tra các node thực sự được nối và khởi động; bao gồm resume bị từ chối hoặc resolve nhưng vẫn suspended. Mute được lưu và giữ khi đổi clip; video nguồn tắt tiếng không làm tắt âm báo AI.
- HTML được phân tích cấu trúc để xác nhận banner thuộc monitor panel và nằm ngoài video-stage/video-wrap. CSS đặt banner trong luồng bố cục, không phủ lên video.

Node test dùng DOM, đồng hồ và phản hồi HTTP giả lập để kiểm tra chức năng/race. Đây không phải đo độ chính xác AI, bằng chứng phát hiện sự cố thật hoặc kiểm thử browser/loa/điện thoại.

**Thay thế hành vi cũ:** kiểm thử ngày 28/10 từng khóa chọn video khi upload/submit. Yêu cầu mới ngày 29/10 cho phép đổi video và tự hủy phiên cũ; regression hiện tại kiểm tra luồng mới này, không còn yêu cầu khóa nút thư viện.

## Trình duyệt còn bị chặn

Đã đọc Computer Use skill `26.1023.50603`, khởi tạo `@oai/sky`, gọi `list_apps()` thành công. Ngày 29/10, inventory có một cửa sổ mang tên AquaWatch trong Chrome. Khi chọn chính cửa sổ được công cụ trả về, thao tác tiếp tục bị từ chối:

> Computer Use was not approved to use Google Chrome

Đã dừng sau khi bị từ chối; không nhập liệu, mở tab hoặc dùng đường khác để vượt quyền. Chưa có screenshot, kiểm chứng bố cục desktop/mobile, bằng chứng nghe âm báo hoặc thử quyền Notification/Vibration từ lượt này. Server/GPU do agent chính quản lý; lượt QA này không mở server trùng hoặc chạy inference cạnh tranh.

## Cần kiểm chứng khi được cấp quyền Chrome

1. Nhấn một CCTV trong thư viện hoặc tải tệp, xác minh video tự phát/nhận diện mà không cần thao tác phân tích thứ hai.
2. Đổi clip nhiều lần khi phiên đang chạy và khi upload còn chờ; xác minh chỉ clip mới nhất được nhận diện, phiên trước được dừng.
3. Kiểm tra bộ đệm, tạm dừng/tiếp tục, tua trong phần đã xử lý và chặn tua vượt frontier; đối chiếu box/banner/lịch sử với thời điểm video.
4. Bật và thử âm báo, tắt âm ngay, xác nhận đã xem, mở lại lịch sử, hủy và xem partial; thử tùy chọn phân tích lại sau khi phiên kết thúc.
5. Kiểm tra laptop và điện thoại thật; ghi rõ các giới hạn autoplay, codec, Notification và Vibration trên thiết bị.
