# Thư viện video trên mặt nước

Đã tải nguồn thật, kiểm tra hình ảnh và tạo **13 clip MP4 H.264, tổng 334,5 giây** trong `data/library/clips/`. Có sáu đoạn âm tính với người trong bể, một đoạn nền không có người, bốn đoạn diễn tập chới với/nổi thụ động/hỗ trợ, một diễn tập cứu hộ ven biển và một vụ cứu hộ thật. Có 10 bản nguồn được chọn, gom bảo thủ thành 8 nhóm nguồn/sự kiện. Đây là video chuyển động thật, không ghép ảnh tĩnh hoặc dựng kết quả AI.

Catalog: `data/video_library.json`. Mỗi clip có file/hash, source URL/credit/license, hash bản nguồn, khoảng cắt gốc, FPS/duration/dimensions, loại camera, vai trò kiểm tra và nhãn quan sát theo thời gian. Toàn bộ thư viện giữ ngoài dữ liệu huấn luyện local.

## Các clip hiện có

| Clip local | Giây | Nội dung/nhãn quan sát | Camera và phạm vi |
|---|---:|---|---|
| `pool_normal_lane_35s.mp4` | 35 | Vận động viên nghỉ, trao đổi và hoạt động có kiểm soát trong lane; negative khó vì có động tác đứng nước. | Một góc nhìn poolside ổn định, không cắt cảnh trong đoạn. |
| `pool_normal_orient_15s.mp4` | 15 | Diễn tập định hướng và bơi chủ động; negative, không quan sát tình huống khẩn cấp. | Một góc nhìn trên bờ ổn định. |
| `pool_empty_reflections_48s.mp4` | 48 | Bể không có người, mặt nước phản chiếu; **background negative**, không phải video người bơi bình thường. | Có dịch khung nhẹ; kiểm nhiễu mặt nước, không coi là CCTV tĩnh đã hiệu chuẩn. |
| `pool_staged_active_18s.mp4` | 18 | Người đóng vai nạn nhân chủ động, người hỗ trợ chuẩn bị/tiếp cận. | Góc rộng ổn định trên mặt nước; tình huống **diễn tập**. |
| `pool_staged_assist_18s.mp4` | 18 | Đưa vật nổi và hỗ trợ người diễn tập di chuyển. | Góc gần ổn định; cùng nguồn với clip active, không tính như nguồn độc lập. |
| `pool_staged_passive_9s.mp4` | 9 | Người đóng vai nạn nhân nổi thụ động; không xác nhận bất tỉnh thật. | Chỉ giữ góc rộng quay trên bờ; loại cảnh camera underwater phía sau trong bản nguồn. |
| `beach_watercraft_drill_16s.mp4` | 16 | Diễn tập tiếp cận bằng mô tô nước, người chờ hỗ trợ trên mặt nước. | Camera đổi khung, có một edit gốc khoảng giây 6; **secondary motion/scene-cut stress**, không dùng làm CCTV chính. |
| `beach_usbp_rescue_full.mp4` | 105,5 | Vụ cứu hộ thật tại Imperial Beach theo cơ quan phát hành; nhãn là bối cảnh cứu hộ, chưa có onset/ID nạn nhân chính xác từng frame. | Camera quan sát từ bờ có pan/zoom; secondary motion/domain stress. |
| `pool_normal_edge_32s.mp4` | 32 | Nghỉ ở mép bể, người bơi qua phía trước; negative khó có che khuất. | Một góc nhìn ổn định liên tục; cùng sự kiện Navy với normal lane, không tính nguồn độc lập. |
| `pool_normal_goggles_12s.mp4` | 12 | Vận động viên đứng nước/chỉnh kính; negative khó có tay đưa lên đầu. | Góc nhìn trên bờ ổn định; nguồn Invictus 2025. |
| `pool_normal_backstroke_13s.mp4` | 13 | Bơi ngửa chủ động; negative. | Camera pan theo người; secondary motion, cùng nhóm Invictus. |
| `pool_normal_race_8s.mp4` | 8 | Bơi thi đấu, nước bắn và che khuất một phần; negative ngắn. | Camera theo người bơi từ bờ; secondary motion, nguồn Warrior Games 2024. |
| `pool_staged_buddy_tow_5s.mp4` | 5 | Tiếp cận/hỗ trợ người đóng vai có vật nổi; diễn tập SAR. | Đoạn ngắn ổn định, không giữ các cảnh underwater trong nguồn Sasebo 2014. |

“Góc nhìn ổn định” là điều quan sát trong đoạn video, **chưa xác nhận camera được lắp CCTV cố định**. Tám đoạn pool có framing ổn định phù hợp kiểm tra flow và các dấu hiệu temporal ban đầu; vẫn cần footage CCTV lắp đặt cố định dài hơn, nhiều nguồn/camera khi đánh giá triển khai cuối. Không cộng nhiều đoạn cùng nguồn thành nhiều sự cố độc lập. Các đoạn ngắn 5–13 giây không thay thế bài kiểm tra cảnh dài.

## Nguồn và giấy phép

- Đoạn normal lane/nghỉ và bơi từ [Navy Wounded Warrior Trials Swimming B-Roll](https://www.dvidshub.net/video/880397/navy-wounded-warrior-trials-swimming-b-roll), Jonathan Snyder, Alexa Trafton, Samuel Tyson / Defense Media Activity - Navy Production, 30/03/2023. Library dùng đoạn 113–148 và 180–212 giây.
- Hai đoạn negative từ [JBLM Training Camp — Swimming B-Roll](https://www.dvidshub.net/video/951507/jblm-training-camp-swimming-b-roll-package), Anthony Beauchamp / U.S. Army Transformation and Training Command, 05/02/2025; giữ 60–72 và 174–187 giây.
- Đoạn bơi thi đấu từ [2024 DoD Warrior Games Swimming](https://www.dvidshub.net/video/929329/2024-dod-warrior-games-swimming), Maurice Moore / Warrior Games, 29/06/2024; giữ 93–101 giây.
- Đoạn buddy-tow từ [Broll of Search and Rescue Training](https://www.dvidshub.net/video/364098/broll-search-and-rescue-training), Krystina Coffey / AFN Sasebo, 25/09/2014; chỉ giữ 198–203 giây. Bản nguồn có camera underwater ở các khoảng khác; không dùng nguyên bản.
- Đoạn normal orient từ [S3T — Orient to Safety](https://www.dvidshub.net/video/741399/swim-survival-skills-training-s3t-orient-safety), Michael Stevenson / Marine and Family Programs; đoạn gốc 7–22 giây.
- Active và assist từ [S3T — Active Drowning Victim](https://www.dvidshub.net/video/741392/swim-survival-skills-training-s3t-conduct-buddy-assist-active-drowning-victim), cùng tác giả/cơ quan; lần lượt 19–37 và 41–59 giây. Passive từ [S3T — Conduct Buddy Assist](https://www.dvidshub.net/video/743307/swim-survival-skills-training-s3t-conduct-buddy-assist-whole-video), 26–35 giây.
- [Train the Trainer Rescue Watercraft Course](https://www.dvidshub.net/video/954300/train-trainer-rescue-watercraft-course-mcbh), Cpl Dezmond Browning / Marine Corps Base Hawaii, 26/02/2025; dùng 47–63 giây.
- [USBP Rescues Drowning Man](https://www.dvidshub.net/video/812817/usbp-rescues-drowning-man), Matthew Dyman / U.S. Customs and Border Protection, 01/09/2021; dùng 0–105,5 giây từ bản nguồn khoảng 105,6 giây.
- Các trang DVIDS trên ghi **PUBLIC DOMAIN**, áp dụng [DVIDS usage notice](https://www.dvidshub.net/about/copyright). Ghi công và không ngụ ý cơ quan/người trong video chứng thực ứng dụng. Thông báo: “The appearance of U.S. Department of War (DoW) visual information does not imply or constitute DoW endorsement.”
- Clip nền từ [Swimming pool 1 2019-02-23.webm](https://commons.wikimedia.org/wiki/File:Swimming_pool_1_2019-02-23.webm), **FASTILY**, own work; [CC BY-SA 4.0](https://creativecommons.org/licenses/by-sa/4.0/). Dùng bản chuyển mã 480p chính thức, cắt 1–49 giây, bỏ âm và mã hóa H.264. Clip phái sinh này tiếp tục CC BY-SA 4.0, giữ ghi công/link giấy phép và mô tả thay đổi.

## Kiểm tra và cách sử dụng

Đã xem contact sheets trải toàn timeline nguồn, rồi xem clip đã xuất mỗi 1 giây, riêng USBP dài lấy mỗi 2 giây; có kiểm tra các biên đoạn. Không phát hiện camera underwater trong **các đoạn được chọn**. Đây là kiểm tra mẫu dày phủ thời gian, không tuyên bố duyệt bằng mắt từng frame. Bản nguồn có góc underwater được giữ riêng để truy xuất/kiểm tra; **không đưa bản mixed nguyên gốc vào thư viện trình diễn**. Review sheets nằm trong `data/library/review/`.

Kết quả giải mã toàn bộ clip bằng FFmpeg tới null output, SHA-256 và dung lượng thực được lưu trong `data/library/video_decode_checks.json` và catalog. Kiểm tra decode không thay thế việc kiểm thử phát/âm báo trong ứng dụng.

Mỗi clip giữ một khoảng thời gian liên tục của nguồn, không thay tốc độ, không đảo thứ tự, không thêm cảnh/khung giả; chuyển H.264/30 FPS để trình duyệt phát ổn định. Việc đổi FPS là resampling playback, không sinh nhãn AI. Với clip secondary watercraft, edit đã có trong nguồn và được khai báo.

Nhãn trong `annotations` là hành vi/bối cảnh quan sát được và tính chất diễn tập. Chưa có nhãn bounding box/track ID hoặc onset/end sự cố được thẩm định để tính accuracy y khoa. Có thể dùng sáu đoạn normal tổng 115 giây để đếm alarm giả quan sát được, nhưng thời lượng và số nhóm nguồn còn quá ít để suy ra FP/hour ổn định; không xem bể trống thay thế người lặn/bơi/vui chơi negative khó.

Trong lượt bổ sung cũng đã tải và duyệt [Coast Guardsmen Conduct Rescue Swimmer Training](https://www.dvidshub.net/video/298303/coast-guardsmen-conduct-rescue-swimmer-training) và [End of Summer Bash Iwakuni 2026](https://www.dvidshub.net/video/1019141/end-summer-bash-mcas-iwakuni-japan-2026-b-roll). Hai bản này chỉ nằm ở `raw/`: bản thứ nhất phần lớn là camera sát/dưới mặt nước; bản thứ hai montage chủ yếu hoạt động ngoài bể, các shot bơi quá ngắn. **Không nhập vào catalog trình diễn**, dù trang nguồn ghi Public Domain. Bản ZIP randhana và video Kaggle có provenance footage chưa rõ cũng không tự động được dùng vì giấy phép phần mềm MIT.

Thư viện **không dùng trong fine-tuning local**. Không biết dữ liệu upstream của checkpoint cộng đồng có chứa các nguồn này hay không, nên chưa gọi độc lập hoàn toàn với pretraining. Các video S3T được gom bảo thủ vào `source_group=s3t_pool_training_2020`; nếu dùng thư viện để chỉnh model/threshold thì không còn là tập test cuối. Không tự đưa chúng vào train khi mở rộng dataset.

## Tái hiện và tích hợp

```powershell
.venv\Scripts\python.exe -m pip install imageio-ffmpeg==0.6.0
.venv\Scripts\python.exe scripts/fetch_video_library.py
```

Script tải các nguồn được chọn nếu chưa cache, ghi SHA-256 và cắt đúng các khoảng đã duyệt. `--rebuild` tạo lại clip từ nguồn cache. Catalog chỉ đánh dấu file sau khi mở/đọc metadata được; lỗi tải/encode làm lệnh thất bại. Để kiểm toàn bộ giải mã có thể dùng FFmpeg do `imageio_ffmpeg.get_ffmpeg_exe()` cung cấp.

Backend có thể đọc `videos[]`, phục vụ `data/library` qua `/media/library`, chỉ hiển thị các `url`/`thumbnail_url` trong catalog. Giữ các field `scenario`, `nature`, `camera_support`, source/license và annotations khi nhập vào metadata video. Script này **không sửa SQLite/API/UI**; việc đăng ký trong ứng dụng do luồng tích hợp thực hiện.
