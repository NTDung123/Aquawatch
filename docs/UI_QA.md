# Kiểm tra giao diện AquaWatch

Ngày kiểm tra: 28/10/2026. Phạm vi: giao diện local trong `web/` và luồng phát lại video có sẵn theo thời gian. Không kết nối camera vật lý.

## Kết quả đã thực hiện

- `node --check web/app.js`: đạt.
- `node tests/frontend_timeline.test.cjs`: đạt; xác minh 79 liên kết phần tử HTML.
- Kiểm tra logic bằng DOM và dữ liệu thử: lấy sample phía trước hoặc đúng thời điểm đang xem; không dùng sample tương lai; không giữ box quá lâu; không hiển thị ID sự kiện tương lai khi đang giám sát; cập nhật snapshot không lặp âm báo cho cùng sự kiện.
- Kiểm tra bộ đệm: video và thao tác tua bị chặn tại `processed_until`; thiếu kết quả thì tạm dừng; có thêm dữ liệu chỉ tiếp tục nếu người dùng vẫn muốn phát; thao tác tạm dừng của người dùng được giữ; phiên hủy giữ giới hạn phần đã xử lý.
- Kiểm tra race khi gửi yêu cầu/tải video: lọc hoặc dựng lại thư viện vẫn giữ nút chọn bị khóa; không đổi video hoặc thế hệ yêu cầu khi thao tác còn đang chờ.
- Kiểm tra thông tin thư viện: phân biệt cảnh bơi/nền âm tính với tình huống diễn tập/cứu hộ; tìm kiếm tiếng Việt không dấu; góc quay ổn định chưa được xem là bằng chứng vị trí lắp camera đã xác minh.

Các dữ liệu và DOM trong Node test là dữ liệu thử cho chức năng phần mềm. Chúng không phải kết quả đánh giá AI, phép đo độ chính xác hoặc bằng chứng hệ thống nhận diện được sự cố thật.

## Kiểm tra trình duyệt còn thiếu

Đã đọc Computer Use skill phiên bản `26.1023.50603`, khởi tạo `@oai/sky` và gọi `list_apps()` thành công. Khi chọn cửa sổ Google Chrome thực được trả về, công cụ từ chối với thông báo nguyên văn:

> Computer Use was not approved to use Google Chrome

Không thực hiện thao tác nhập liệu, mở tab hoặc điều khiển Chrome sau khi bị từ chối. Không có ảnh chụp giao diện, kiểm chứng bố cục desktop/mobile, phép thử nghe âm báo hoặc quyền thông báo/rung từ lượt kiểm tra này.

Tại lần thăm dò đầu lượt, `http://127.0.0.1:8000/api/status` không kết nối được. Agent chính quản lý việc khởi động lại server và GPU; lượt QA này không tự mở thêm server hoặc chạy inference cạnh tranh.

## Các bước cần kiểm chứng khi có quyền Chrome

1. Mở ứng dụng, chọn clip trong thư viện, kiểm tra thông tin nguồn/giấy phép, khai báo góc quay và bắt đầu chế độ CCTV phát lại.
2. Quan sát video đang phát trong lúc job còn chạy; kiểm tra bộ đệm khi AI chậm, tạm dừng/tiếp tục, tua về trước và chặn tua vượt frontier.
3. Đối chiếu overlay, banner và lịch sử với thời điểm video. Thử âm báo sau thao tác bật chủ động, xác nhận đã xem và tắt âm ngay.
4. Dừng phiên giữa chừng, mở lại phần kết quả đã lưu, thử chế độ phân tích toàn bộ và xuất báo cáo khi hoàn tất.
5. Kiểm tra ở kích thước laptop và điện thoại; ghi rõ giới hạn thực tế của autoplay, Notification và Vibration trên thiết bị.
