# Hướng dẫn sử dụng PRANA ELEX

Tài liệu này mô tả luồng sử dụng Android App với Laptop hoặc Raspberry Pi
Station. Xem [Cài đặt và phát triển](getting-started.md) nếu hệ thống chưa được
cài đặt.

## Đăng ký và đăng nhập

1. Mở App, chọn **Tạo tài khoản** hoặc đăng nhập bằng Google.
2. Với Email/Password, mở email xác minh rồi quay lại App và làm mới trạng thái.
3. Mở **Tài khoản** để xem gói, quota, thiết bị và Station đang sở hữu.

Không chia sẻ mật khẩu, token hoặc QR Station trong ảnh chụp báo lỗi.

## Ghép Station

1. Bảo đảm Station service đang online và có Internet.
2. Trong danh sách Station, chọn **Ghép trạm**.
3. Quét QR cố định trên Laptop/Raspberry Pi hoặc nhập Setup ID và Activation Code.
4. Pairing code tạm thời 8 ký tự chỉ dành cho luồng cũ còn tương thích.
5. Sau khi ghép thành công, Station xuất hiện trong danh sách của tài khoản.

Một Station chỉ thuộc một owner tại một thời điểm. Muốn chuyển owner, phải gỡ
Station hoặc thực hiện transfer theo quy trình Admin.

## Cấu hình Station

Mở Station rồi nhấn biểu tượng bánh răng:

1. Nhấn **Quét lại thiết bị** nếu vừa cắm USB SoundCard.
2. Chọn đúng `RX INPUT` có input channel.
3. Chọn đúng `TX OUTPUT` có output channel.
4. Quay lại màn vận hành và chờ Station đồng bộ desired state.

Nếu App không tìm thấy USB SoundCard, kết nối lại thiết bị rồi nhấn **Thử lại**.
Không để START mắc ở trạng thái chờ vô hạn; xem
[Troubleshooting](troubleshooting.md#start-mắc-ở-đang-bật).

## Sử dụng RX

1. Chọn ngôn ngữ đầu vào hoặc chế độ nhận diện phù hợp.
2. Chọn ngôn ngữ đầu ra.
3. Nhấn **START** và chờ badge chuyển sang `RX LISTENING`.
4. Phát audio VHF vào USB SoundCard.
5. Theo dõi transcript, bản dịch, ngôn ngữ và độ tin cậy trong phần Live.
6. Nhấn biểu tượng loa để nghe lại:
   - source khác target: App đọc bản dịch bằng TTS;
   - source trùng target: App phát WAV nguồn;
   - không tải được WAV: App fallback sang TTS transcript.
7. Bật hoặc tắt auto-play bằng nút audio trong Live Translations.

RX tạo segment khi gặp khoảng nghỉ đã cấu hình hoặc đạt giới hạn 15 giây. Một
lượt nói dài có thể tạo nhiều card liên tiếp để giới hạn latency và kích thước
request.

## Sử dụng TX Hold-to-talk

TX chỉ hoạt động khi Station online, đã START và không có command đang chờ.

1. Chọn **Ngôn ngữ TX** ở bên phải bottom dock.
2. Nhấn giữ **GIỮ ĐỂ NÓI** trong suốt lúc nói.
3. Khi dock chuyển đỏ và timer chạy, App đang thu microphone điện thoại.
4. Thả nút để upload WAV và nhận dạng/dịch.
5. Tại màn review:
   - transcript gốc chỉ đọc;
   - bản dịch/nội dung phát có thể chỉnh sửa;
   - nội dung không được rỗng và tối đa 2.000 ký tự.
6. Chọn **Phát** để tạo audio, nối khoảng lặng và từ “Over”; chọn **Hủy** để bỏ draft.
7. Theo dõi trạng thái:

   ```text
   Đang tổng hợp → Đang chờ Station → Station đang phát → Hoàn tất
   ```

Station dừng RX trước playback và chỉ resume nếu desired state vẫn là START.
Job lỗi không tự phát lại để tránh truyền trùng; chỉ nhấn **Thử lại** sau khi
Station online và START trở lại.

Trên Raspberry Pi có PTT, Station đưa GPIO17 lên HIGH, chờ key-up 400 ms, phát
audio, giữ tail 300 ms rồi hạ GPIO. Watchdog 122 giây luôn nhả PTT nếu player
treo. Nếu GPIO không khởi tạo được, RX và heartbeat vẫn chạy nhưng TX bị khóa
với `PTT_UNAVAILABLE`. Laptop Station dùng PTT thủ công. Hệ thống chưa có
channel-busy sensing.

## Xem lịch sử

1. Nhấn biểu tượng **Lịch sử** trong phần Live Translations.
2. Chọn tab `RX` hoặc `TX`; tab mặc định là RX.
3. Chọn ngày để xem log chi tiết.
4. Tab RX hiển thị transcript/bản dịch và playback theo entitlement.
5. Tab TX hiển thị transcript, nội dung đã phát, trạng thái, attempt và dấu hiệu
   chỉnh sửa; nút loa phát output WAV nếu job đã tạo audio.

Quyền xem lịch sử và độ trễ mở khóa phụ thuộc gói hiện tại.

## STOP, offline và đăng xuất

- Nhấn **Dừng** để đặt desired state `running=false`.
- Nếu Station offline, STOP vẫn được lưu để Station không tự chạy RX khi kết nối lại.
- Nếu mất mạng giữa TX, chờ backend giải phóng job rồi mới retry thủ công.
- Đăng xuất, đổi Station hoặc đưa App xuống background sẽ dừng playback trên điện thoại.
