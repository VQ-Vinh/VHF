# Hướng dẫn kiểm thử Android App và Web Admin

> **Chú ý phạm vi:** Tài liệu này chỉ kiểm thử phần RX (thu audio, nhận
> dạng/dịch, hiển thị và phát giọng nói bản dịch). Không kiểm thử TX, PTT, phát
> RF hoặc truyền audio từ App/Station trở lại máy vô tuyến vì các chức năng đó
> chưa thuộc sản phẩm hiện tại.

## 1. Mục đích

Tài liệu này dành cho đội ngũ tester kiểm thử thủ công PRANA ELEX trên môi
trường staging. Tester không cần đọc source code.

Phạm vi gồm:

- Android App: đăng ký, đăng nhập, ghép Station, điều khiển, xem Live, History,
  Account và xử lý mất mạng.
- Web Admin: đăng nhập, Dashboard, Users, Plans, Stations và Audit log.
- Luồng xuyên hệ thống giữa Android App, Station và Web Admin.

Không sử dụng tài khoản, audio hoặc Station thật của khách hàng.
Trong toàn bộ tài liệu, Start/Stop Station có nghĩa là Start/Stop thu và xử lý
RX; không có nghĩa là điều khiển phát sóng.

## 2. Cách ghi nhận kết quả

Mỗi test case phải được ghi một trong các trạng thái:

- **PASS:** kết quả thực tế giống kết quả mong đợi.
- **FAIL:** chức năng chạy nhưng kết quả sai.
- **BLOCKED:** không thể kiểm thử do thiếu tài khoản, dữ liệu hoặc môi trường.
- **NOT RUN:** chưa thực hiện.

Khi FAIL, ticket lỗi cần có:

1. Mã test case.
2. Phiên bản APK, API, Web Admin và Station.
3. Thiết bị, phiên bản Android, trình duyệt và múi giờ.
4. Tài khoản và Station ID đã che bớt thông tin nhạy cảm.
5. Các bước tái hiện.
6. Kết quả thực tế và kết quả mong đợi.
7. Ảnh hoặc video; request ID nếu màn hình có hiển thị.

Không chụp hoặc đưa vào ticket access token, password, activation code đầy đủ,
private key, CSRF token hay credential Google Cloud.

## 3. Chuẩn bị môi trường và dữ liệu

### 3.1. Thiết bị

- Một điện thoại Android 10 trở lên đã cài APK staging mới nhất.
- Có thể thay đổi múi giờ và cỡ chữ trên điện thoại.
- Chrome hoặc Edge bản mới để kiểm thử Web Admin.
- Một Laptop/Pi Station đã provision và có nguồn audio tiếng Việt/Anh.
- Laptop/Pi và điện thoại có thể kết nối hai mạng Internet khác nhau để xác
  nhận vận hành từ xa qua Cloud API.
- Mạng có thể chủ động tắt/bật để kiểm tra offline.

### 3.2. Tài khoản

Chuẩn bị các tài khoản riêng:

| Tên dùng trong tài liệu | Trạng thái |
|---|---|
| User A | Đã xác minh email, plan Free |
| User B | Đã xác minh email, còn quyền nhận thêm Station |
| User Pro | Đã xác minh, plan cho phép xem History ngay |
| User Unverified | Chưa xác minh email |
| Admin | Có quyền IAP và nằm trong allowlist |
| Non-admin | Tài khoản Google không có quyền Admin |

### 3.3. Dữ liệu lịch sử

Nhờ người quản trị staging chuẩn bị:

- Nhiều session có log trong cùng một ngày.
- Một session có log trước và sau 00:00.
- Một ngày có hơn 1.000 log để kiểm tra phân trang.
- Log có cả tiếng Việt, tiếng Anh, dấu phẩy và dấu ngoặc kép để test export.
- Một Station online, một Station offline và một Station có lỗi.

### 3.4. Kiểm tra trước khi bắt đầu

Ghi lại:

- Phiên bản APK và Station.
- Revision API và Web Admin.
- Múi giờ điện thoại.
- Thời gian bắt đầu test.

Xác nhận màn hình Station báo `API READY` và `ONLINE` trước các case cần thu âm.
Ở luồng khách hàng, chạy `enable_station_api.bat` không được yêu cầu cài
`gcloud`, đăng nhập ADC hoặc nhập credential Google Cloud.

---

## 4. Android App — tài khoản

### AND-AUTH-01 — Đăng ký bằng email

**Các bước**

1. Xóa dữ liệu App hoặc đăng xuất.
2. Xác nhận mặc định là tab Sign in, sau đó chuyển sang tab Sign up.
3. Bấm Create account khi cả ba trường đang trống.
4. Lần lượt nhập email sai định dạng; mật khẩu dưới 6 ký tự, thiếu chữ hoa,
   thiếu chữ số; mật khẩu xác nhận không khớp và form hợp lệ.
5. Chuyển qua lại hai tab rồi gửi form hợp lệ.

**Kết quả mong đợi**

- App báo lỗi ngay tại trường sai và không bị crash.
- App không gọi Firebase khi form sai và không hiển thị exception dạng
  `dev.flutter.pigeon...`.
- Email/Password được giữ khi đổi tab; lỗi không còn liên quan được xóa.
- Tab Sign up hiển thị nút **Sign up with Google** thay cho
  **Continue with Google**.
- Tài khoản hợp lệ được tạo một lần.
- App chuyển đến màn hình xác minh email và chưa cho sử dụng tính năng Station.

### AND-AUTH-02 — Xác minh email

**Các bước**

1. Đăng nhập bằng User Unverified.
2. Thử mở danh sách Station.
3. Mở email xác minh và bấm liên kết.
4. Quay lại App và bấm **Tôi đã xác minh**.
5. Kiểm tra nút gửi lại bị cooldown 60 giây và Sign out vẫn hoạt động.

**Kết quả mong đợi**

- Trước khi xác minh, chức năng nghiệp vụ bị khóa với hướng dẫn rõ ràng.
- Route Station luôn chuyển về màn hình xác minh khi email chưa xác minh.
- Sau khi xác minh, tài khoản được dùng App và nhận plan mặc định.

### AND-AUTH-03 — Đăng nhập Google

**Các bước**

1. Đăng nhập bằng một Google account mới.
2. Lặp lại từ cả tab Sign in và Sign up; hủy hộp chọn tài khoản một lần.
3. Đăng xuất và đăng nhập lại bằng cùng account.
4. Nếu có account Email/Password cùng email, thử liên kết Google.

**Kết quả mong đợi**

- Không tạo hai người dùng cho cùng một danh tính.
- Hủy Google Sign-in không hiển thị lỗi.
- Đăng nhập lại mở đúng dữ liệu của người dùng đó.
- Không hiển thị token hoặc thông tin lỗi nội bộ.

### AND-AUTH-04 — Quên mật khẩu và đăng xuất

**Các bước**

1. Bấm Sign in khi Email/Password trống và xác nhận chỉ có lỗi tại trường.
2. Yêu cầu đặt lại mật khẩu khi Email trống/sai, sau đó dùng Email hợp lệ.
3. Dùng email nhận được để đặt mật khẩu mới.
4. Thử mật khẩu cũ và mật khẩu mới.
5. Đóng/mở App; bấm Sign out, chọn Cancel rồi thực hiện lại và xác nhận.

**Kết quả mong đợi**

- Mật khẩu cũ không còn dùng được; mật khẩu mới đăng nhập thành công.
- App ghi nhớ phiên khi đóng/mở.
- Cancel giữ nguyên phiên; xác nhận Sign out xóa phiên và đưa về Sign in.

---

## 5. Android App — ghép và quản lý Station

### AND-PAIR-01 — Ghép Station bằng QR

**Các bước**

1. Đăng nhập User A và chọn thêm Station.
2. Quét QR hợp lệ được tạo bởi `generate_station_qr.bat`.
3. Xác nhận ghép.
4. Quét lại cùng QR bằng User A.

**Kết quả mong đợi**

- Station xuất hiện trong danh sách của User A.
- Quét lại không tạo Station trùng.
- App không hiển thị activation code sau khi hoàn tất.

### AND-PAIR-02 — QR không hợp lệ hoặc đã có chủ

**Các bước**

1. Quét QR sai, QR bị sửa hoặc Station đang thuộc tài khoản khác.
2. Đăng nhập User B và quét QR Station đang thuộc User A.

**Kết quả mong đợi**

- App từ chối với thông báo dễ hiểu.
- Không Station nào bị đổi chủ hoặc tạo trùng.
- User B không xem được dữ liệu của User A.

### AND-PAIR-03 — Giới hạn số Station

**Các bước**

1. Dùng tài khoản đã đạt giới hạn Station của plan.
2. Thử ghép thêm một Station hợp lệ.

**Kết quả mong đợi**

- App thông báo đã đạt giới hạn.
- Station cũ và Station mới không bị thay đổi sai.

### AND-PAIR-04 — Pairing tạm thời

**Các bước**

1. Cho Station tạo pairing code tạm thời.
2. Ghép bằng deep link hoặc nhập code 8 ký tự trong vòng 10 phút.
3. Đăng xuất, dùng User B thử lại cùng code.
4. Tạo code khác, chờ hết 10 phút rồi thử ghép.
5. Nhập sai code nhiều lần theo giới hạn được phép của môi trường test.

**Kết quả mong đợi**

- Code hợp lệ ghép đúng Station và chỉ sử dụng được một lần.
- Code đã dùng, sai hoặc hết hạn đều bị từ chối.
- Không tạo Station trùng hoặc đổi owner khi bị từ chối.
- Khi thử sai liên tục, App báo tạm giới hạn thay vì gửi không giới hạn.

### AND-STA-01 — Trạng thái online/offline

**Các bước**

1. Mở danh sách Station khi Station đang chạy.
2. Tắt Station và chờ ít nhất 15 giây.
3. Chạy Station trở lại.

**Kết quả mong đợi**

- Trạng thái lần lượt là online, offline rồi online.
- Có thể mở đúng Station từ danh sách.
- App không cần đăng nhập lại khi Station kết nối trở lại.

---

## 6. Android App — Live và điều khiển

### AND-LIVE-01 — Start, Stop và đổi ngôn ngữ

**Các bước**

1. Mở Station online.
2. Chọn ngôn ngữ đích và bấm Start.
3. Phát audio rõ, mỗi đoạn dưới 15 giây.
4. Đổi ngôn ngữ đích rồi phát thêm audio.
5. Bấm Stop.

**Kết quả mong đợi**

- Nút hiển thị trạng thái đang chờ trong lúc gửi lệnh.
- Station bắt đầu/dừng thu đúng lệnh cuối cùng.
- Transcript, bản dịch, ngôn ngữ và thời gian hiển thị đúng.
- Không tạo bản dịch mới sau khi Stop đã được Station nhận.

### AND-LIVE-02 — Station offline

**Các bước**

1. Ngắt Station cho tới khi App báo offline.
2. Thử Start, Stop và thay đổi cài đặt.
3. Kết nối lại Station.

**Kết quả mong đợi**

- Các thao tác không hợp lệ bị khóa hoặc báo lỗi rõ ràng.
- App không crash và không mất các log đang hiển thị.
- Sau khi online lại, người dùng có thể tiếp tục thao tác.

### AND-LIVE-03 — Retry khi xử lý audio lỗi

**Các bước**

1. Tạo một đoạn audio lỗi theo dữ liệu test.
2. Chọn Retry.
3. Quan sát trạng thái cho đến khi hoàn tất.

**Kết quả mong đợi**

- Chỉ đoạn lỗi được xử lý lại.
- Không tạo kết quả trùng.
- Thông báo tiến trình và kết quả cuối rõ ràng.

### AND-LIVE-04 — Không xử lý trùng một yêu cầu

Case này cần người quản trị hoặc công cụ test gửi lại cùng một request ID.

**Các bước**

1. Gửi một đoạn audio hợp lệ và ghi lại request ID.
2. Gửi lại đúng audio với cùng request ID.
3. Gửi audio khác nhưng vẫn dùng request ID đó.
4. Đối chiếu usage/quota trước và sau.

**Kết quả mong đợi**

- Cùng request ID và cùng dữ liệu trả lại cùng kết quả, không tạo log mới.
- Cùng request ID nhưng dữ liệu khác bị từ chối do xung đột.
- Quota chỉ bị trừ một lần.

### AND-LIVE-05 — Chỉ hiển thị log hôm nay

**Các bước**

1. Dùng dữ liệu có log lúc 23:59 hôm trước và 00:00 hôm nay.
2. Mở Live và chờ ít nhất một vòng refresh.
3. Nếu có thể, giữ màn hình qua 00:00 hoặc dùng môi trường test đổi ngày.

**Kết quả mong đợi**

- Live chỉ hiển thị log thuộc ngày hiện tại theo giờ điện thoại.
- Sau 00:00, log ngày cũ tự biến mất mà không cần khởi động lại App.
- Log cũ vẫn xem được trong History khi đã mở khóa.

### AND-LIVE-06 — Quota và giới hạn log

**Các bước**

1. Dùng tài khoản gần hết quota và tạo thêm kết quả.
2. Tạo kết quả cho tới khi hết quota.
3. Dùng plan có giới hạn Live và plan không giới hạn.

**Kết quả mong đợi**

- App cảnh báo khi gần hết quota.
- Hết quota thì không xử lý thêm và giải thích rõ lý do.
- Live tuân theo giới hạn của từng plan; giá trị `0` được hiểu là không giới hạn.

### AND-SET-01 — Cài đặt audio

**Các bước**

1. Mở cài đặt Station.
2. Không thay đổi gì và quan sát nút Save.
3. Đổi audio device/capture mode, sau đó đổi về giá trị ban đầu.
4. Thay đổi hợp lệ và Save.

**Kết quả mong đợi**

- Chỉ hiển thị lựa chọn Station hỗ trợ.
- Save tắt khi không thay đổi hoặc đã hoàn tác.
- Save sáng khi dữ liệu hợp lệ và có thay đổi.
- Sau khi lưu, trạng thái App và Station giống nhau.

---

## 7. Android App — History, export và Account

### AND-HIS-01 — Gộp lịch sử theo ngày

**Các bước**

1. Mở History với dữ liệu có nhiều session trong cùng một ngày.
2. Mở thẻ ngày.
3. Cuộn từ đầu tới cuối danh sách.

**Kết quả mong đợi**

- Mỗi ngày chỉ có một thẻ `Ngày dd/MM/yyyy`.
- Không hiển thị tên `session001`, `session002` hoặc session ID.
- Chi tiết ngày chứa log của tất cả session, không thiếu hoặc trùng.
- Log được sắp xếp đúng theo thời gian.

### AND-HIS-02 — Múi giờ và nửa đêm

**Các bước**

1. Mở ngày có log ở hai phía của 00:00.
2. Ghi lại nhóm ngày hiện tại.
3. Đổi múi giờ điện thoại sang múi giờ test khác và tải lại.

**Kết quả mong đợi**

- Log được nhóm theo ngày địa phương của điện thoại.
- Một session chạy qua nửa đêm được chia vào đúng hai ngày.

### AND-HIS-03 — Khóa lịch sử

**Các bước**

1. Đăng nhập User A có History delay 1 ngày.
2. Mở History trong ngày hiện tại.
3. Đăng nhập User Pro có delay 0 và lặp lại.

**Kết quả mong đợi**

- User A thấy ngày hiện tại nhưng thẻ có khóa và không mở được.
- Thẻ mở vào 00:00 ngày hôm sau theo giờ điện thoại.
- User Pro xem được ngày hiện tại ngay.

### AND-HIS-04 — Ngày có hơn 1.000 log

**Các bước**

1. Mở ngày đã chuẩn bị hơn 1.000 log.
2. Cuộn cho tới khi tải hết.
3. So sánh tổng số và các mốc đầu/cuối với dữ liệu chuẩn.

**Kết quả mong đợi**

- Tải đủ dữ liệu qua nhiều trang.
- Không thiếu, trùng hoặc đổi thứ tự bất thường.
- App vẫn phản hồi khi cuộn và tìm kiếm.

### AND-HIS-05 — Tìm kiếm và export

**Các bước**

1. Tìm một từ trong transcript và một từ trong bản dịch.
2. Export ngày dưới dạng TXT và CSV.
3. Mở file bằng trình đọc text và phần mềm bảng tính.

**Kết quả mong đợi**

- Tìm kiếm áp dụng cho toàn bộ log trong ngày.
- Tên file là `prana-YYYY-MM-DD.txt` hoặc `.csv`.
- File có đủ log, đúng Unicode; CSV không vỡ cột khi nội dung có dấu phẩy hoặc
  dấu ngoặc kép.

### AND-HIS-06 — Ẩn log trên màn hình

**Các bước**

1. Mở chi tiết một ngày và ghi lại tổng số log.
2. Chọn ẩn một log.
3. Tìm kiếm lại nội dung của log vừa ẩn.
4. Đóng rồi mở lại ngày theo hành vi mà bản build đang công bố.

**Kết quả mong đợi**

- Log bị ẩn khỏi danh sách và kết quả tìm kiếm hiện tại.
- Các log khác không bị ảnh hưởng.
- Chức năng ẩn chỉ thay đổi phạm vi UI được công bố, không xóa dữ liệu backend.

### AND-HIS-07 — Thời hạn lưu lịch sử

**Các bước**

1. Mở ngày có dữ liệu gần đủ 14 ngày.
2. Tìm dữ liệu đã quá thời hạn 14 ngày do quản trị viên chuẩn bị.
3. Đối chiếu với thời gian hiện tại và múi giờ điện thoại.

**Kết quả mong đợi**

- Dữ liệu còn trong thời hạn được xem bình thường.
- Dữ liệu hết thời hạn không còn được trả về.
- App không hiển thị thẻ ngày rỗng hoặc báo lỗi khi dữ liệu đã được dọn.

### AND-ACC-01 — Account, device và Station

**Các bước**

1. Mở Account Center.
2. Đối chiếu email, plan, usage và quota.
3. Hủy rồi xác nhận revoke một device test.
4. Hủy rồi xác nhận gỡ một Station test.
5. Đăng nhập User B và claim lại Station bằng tem QR cũ.

**Kết quả mong đợi**

- Thông tin tài khoản khớp dữ liệu staging.
- Hủy dialog không thay đổi dữ liệu.
- Device được thu hồi và không thể tự đăng ký lại.
- Station được gỡ khỏi User A, dừng xử lý và không còn tính vào quota của A.
- User B claim lại cùng QR thành công nhưng không xem được lịch sử của User A.

### AND-ACC-02 — Cho phép device đăng ký lại

**Các bước**

1. Thu hồi một device test và xác nhận device đó không còn truy cập được.
2. Trên Web Admin, cho phép đúng device đó đăng ký lại.
3. Thực hiện enrollment lại trên device.
4. Kiểm tra một device khác của cùng user.

**Kết quả mong đợi**

- Chỉ device được chọn có thể enrollment lại.
- Device khác không bị revoke hoặc thay đổi.
- Audit ghi đúng user, device và Admin thực hiện.

---

## 8. Android App — giao diện và lỗi mạng

### AND-UI-01 — Ngôn ngữ và khả năng truy cập

**Các bước**

1. Đổi qua lại tiếng Việt và tiếng Anh.
2. Đóng và mở lại App.
3. Bật cỡ chữ lớn, TalkBack và xoay màn hình.

**Kết quả mong đợi**

- Nội dung đổi ngôn ngữ đầy đủ và giữ lựa chọn sau khi mở lại.
- Không tràn chữ hoặc mất nút chính.
- TalkBack đọc được tên và trạng thái của control theo thứ tự hợp lý.

### AND-NET-01 — Mất mạng

**Các bước**

1. Mở lần lượt Station list, Live và History.
2. Tắt mạng rồi thử refresh và gửi một thao tác.
3. Bật mạng trở lại.

**Kết quả mong đợi**

- App hiển thị offline/lỗi thân thiện, không crash.
- Không tạo thao tác hoặc log trùng.
- App tự tải lại hoặc cung cấp nút Retry rõ ràng.

### AND-NET-02 — Truy cập Station từ mạng khác

**Các bước**

1. Kết nối Station với mạng Internet A.
2. Tắt Wi-Fi trên điện thoại và dùng 4G/5G hoặc mạng Internet B.
3. Mở App, kiểm tra trạng thái Station, Start RX và tạo một đoạn audio.
4. Mở Live và History; sau đó Stop RX.

**Kết quả mong đợi**

- App báo Cloud API sẵn sàng và Station online dù hai thiết bị không cùng LAN.
- Start/Stop RX, Live result và History hoạt động qua Internet.
- APK không gọi `10.0.2.2`, `127.0.0.1` hoặc IP LAN của Station.
- Không cần port forwarding hay mở inbound port trên router khách hàng.

### OPS-RX-01 — Khởi động Station khách hàng không dùng Google ADC

**Các bước**

1. Dùng máy Windows không có phiên ADC đang hoạt động; không chạy
   `gcloud auth application-default login`.
2. Chạy `enable_station_api.bat`.
3. Kiểm tra process, log Station và trạng thái trên Android/Web Admin.
4. Khởi động lại máy và chạy lại script.

**Kết quả mong đợi**

- Script mặc định không gọi `gcloud`, không mở trình duyệt đăng nhập và không
  yêu cầu tài khoản Google Cloud.
- Station kết nối Cloud API bằng Station identity Ed25519 đã provision.
- Station online và xử lý RX sau mỗi lần khởi động mà không cần đăng nhập lại.
- API local không được khởi động trong luồng khách hàng.
- `-LocalApi` được xem là chế độ developer riêng và mới được phép yêu cầu ADC.

---

## 9. Web Admin

### ADM-SEC-01 — Quyền truy cập

**Các bước**

1. Mở Web Admin khi chưa đăng nhập.
2. Đăng nhập bằng Non-admin.
3. Đăng nhập bằng Admin.

**Kết quả mong đợi**

- Người chưa đăng nhập được yêu cầu đăng nhập.
- Non-admin nhận trang 403 và không thấy dữ liệu quản trị.
- Admin truy cập Dashboard bình thường.

### ADM-SEC-02 — Chống giả mạo form quản trị

Case này cần công cụ test HTTP hoặc DevTools theo hướng dẫn của quản trị viên.

**Các bước**

1. Gửi một POST form không có CSRF token.
2. Lặp lại với token sai và token đã hết hạn.
3. Lấy token của Admin A và thử gửi trong phiên của Admin B.
4. Kiểm tra dữ liệu mục tiêu và Audit log sau mỗi lần.

**Kết quả mong đợi**

- Tất cả request không hợp lệ trả 403.
- Không mutation nào được thực hiện.
- Không tạo audit thành công cho request bị từ chối.
- Response không lộ token, secret hoặc exception nội bộ.

### ADM-DASH-01 — Dashboard

**Các bước**

1. Mở Dashboard.
2. Đối chiếu số user, Station và mục cần xử lý với dữ liệu staging.
3. Mở từng liên kết từ mục cần xử lý.

**Kết quả mong đợi**

- Số liệu và trạng thái đúng.
- Chỉ Station offline/có lỗi, tài khoản chưa xác minh quá hạn và thao tác quản
  trị lỗi/chờ xử lý được đưa vào mục cần xử lý.
- Liên kết mở đúng đối tượng.

### ADM-USR-01 — Tìm kiếm và phân trang User

**Các bước**

1. Tìm theo email và UID.
2. Lọc theo trạng thái và plan.
3. Dùng Previous/Next qua nhiều trang.
4. Tìm một giá trị không tồn tại.

**Kết quả mong đợi**

- Kết quả đúng bộ lọc, không thiếu/trùng khi đổi trang.
- Trạng thái loading và empty state rõ ràng.

### ADM-USR-02 — Suspend, reactivate và reset device

**Các bước**

1. Suspend một User Plus/Pro test.
2. Reactivate cùng user.
3. Reset device của user và thử với UID không tồn tại.

**Kết quả mong đợi**

- User bị suspend/reactivate đúng.
- Reactivate giữ nguyên plan hợp lệ; chỉ gán Free nếu trước đó chưa có plan.
- Reset thu hồi đúng số device.
- UID không tồn tại báo 404 và không tạo audit sai.

### ADM-USR-03 — Re-enrollment một device

**Các bước**

1. Mở user có nhiều device, trong đó một device đã revoked.
2. Chọn cho phép enrollment lại đúng device đó.
3. Kiểm tra danh sách device và Audit log.
4. Thử thao tác với device ID không tồn tại.

**Kết quả mong đợi**

- Chỉ trạng thái của device được chọn thay đổi.
- Các device còn lại giữ nguyên.
- Audit ghi đúng operator, user, device và before/after.
- Device không tồn tại trả lỗi an toàn, không tạo audit sai.

### ADM-PLAN-01 — Chỉnh sửa plan

**Các bước**

1. Mở Plans và thử nhập trực tiếp khi chưa bấm bút chì.
2. Bấm icon bút chì của một plan.
3. Không đổi dữ liệu, đổi rồi hoàn tác, nhập dữ liệu sai.
4. Thay đổi hợp lệ và bấm Save.
5. Kiểm tra preview; lần đầu Cancel, lần sau xác nhận Save.

**Kết quả mong đợi**

- Mọi input mặc định chỉ đọc.
- Chỉ plan được chọn cho phép sửa.
- Save chỉ sáng khi dữ liệu hợp lệ và thực sự thay đổi.
- Cancel khôi phục toàn bộ giá trị ban đầu.
- Xác nhận Save cập nhật plan và hiển thị thông báo thành công.

### ADM-STA-01 — Danh sách và chi tiết Station

**Các bước**

1. Tìm theo Station ID và email owner.
2. Lọc online/offline/error và platform.
3. Mở chi tiết từng Station mẫu.

**Kết quả mong đợi**

- Bộ lọc và phân trang không thiếu/trùng.
- Owner, last seen, capture state, lỗi, platform và app version đúng.
- Chi tiết hiển thị audio device, session hiện tại, trạng thái lệnh và lịch sử
  chuyển chủ.

### ADM-STA-02 — Stop và transfer

**Các bước**

1. Gửi Stop cho Station đang chạy.
2. Thử transfer khi Station vẫn chạy.
3. Sau khi Station idle, nhập sai email xác nhận.
4. Nhập đúng email của User B còn quota và xác nhận.
5. Lặp lại với target đã đạt giới hạn Station.

**Kết quả mong đợi**

- Stop được gửi và trạng thái hội tụ về idle.
- Không transfer Station đang chạy.
- Email xác nhận sai không làm thay đổi dữ liệu.
- Transfer hợp lệ đổi đúng owner; owner cũ mất quyền, owner mới thấy Station.
- Target hết quota bị từ chối và ownership không thay đổi.

### ADM-AUD-01 — Audit log

**Các bước**

1. Lọc theo operator, action, user/Station và khoảng ngày.
2. Chuyển qua nhiều trang.
3. Mở chi tiết các thao tác plan, user, Stop và transfer vừa thực hiện.

**Kết quả mong đợi**

- Không thiếu hoặc trùng bản ghi khi phân trang.
- Mỗi bản ghi có operator, action, target, before/after, request ID và timestamp.
- Thao tác bị hủy hoặc thất bại không tạo audit thành công giả.

### ADM-AUD-02 — Rollback khi mutation hoặc audit thất bại

Case này chỉ chạy khi quản trị viên bật failure injection an toàn trên staging.

**Các bước**

1. Ghi lại trạng thái ban đầu của một user/Station test.
2. Mô phỏng lỗi mutation và gửi thao tác quản trị.
3. Mô phỏng lỗi ghi Audit rồi gửi lại thao tác.
4. Refresh trang chi tiết và Audit log sau mỗi lần.

**Kết quả mong đợi**

- Nếu mutation lỗi, dữ liệu và Audit đều không thay đổi.
- Nếu Audit lỗi, mutation cũng được rollback.
- UI báo lỗi an toàn và cho phép thử lại.

### ADM-UI-01 — Giao diện và trang lỗi

**Các bước**

1. Đổi tiếng Việt/Anh.
2. Thu nhỏ trình duyệt về chiều rộng điện thoại.
3. Điều hướng chỉ bằng bàn phím.
4. Mở URL không tồn tại và tạo các lỗi test được cho phép.

**Kết quả mong đợi**

- Ngôn ngữ được giữ, giao diện không tràn và focus nhìn thấy rõ.
- Dialog dùng được bằng bàn phím.
- Trang 403/404/409/422/500 song ngữ, đúng mã lỗi và không lộ exception,
  stack trace hay secret.

---

## 10. Kiểm thử xuyên hệ thống

### E2E-01 — Admin đổi plan, Android nhận quyền mới

1. Admin đổi `live_log_limit` của User A qua plan.
2. User A refresh Account và tạo thêm log.
3. Admin đổi History delay từ 1 thành 0.
4. User A refresh và mở ngày hiện tại.

**Mong đợi:** App nhận giới hạn mới; Live vẫn chỉ hiện log hôm nay; History ngày
hiện tại mở được sau khi delay bằng 0.

### E2E-02 — Android Start, Admin Stop

1. User A Start Station trên Android.
2. Admin mở Station detail và gửi Stop.
3. Theo dõi Android, Web Admin và Station.

**Mong đợi:** cả ba nơi cuối cùng cùng báo đã dừng; Audit ghi thao tác Stop của
Admin đúng một lần.

### E2E-03 — Transfer Station

1. User A xác nhận đang thấy và điều khiển được Station.
2. Admin transfer Station idle sang User B.
3. Refresh App của cả hai user.

**Mong đợi:** User A mất quyền đọc/điều khiển; User B thấy Station và sử dụng
được; không lộ lịch sử riêng không thuộc quyền của User B.

### E2E-04 — Mất API rồi phục hồi

1. Trong lúc Station hoạt động, dùng môi trường test làm API không khả dụng.
2. Thử Start/Stop và tải History.
3. Khôi phục API và refresh.

**Mong đợi:** giao diện báo lỗi an toàn; không có command, result hoặc audit bị
ghi trùng; hệ thống phục hồi mà không cần xóa dữ liệu App.

### E2E-05 — Suspend user khi Station đang chạy

1. User A Start Station và xác nhận Live đang nhận kết quả.
2. Admin suspend User A.
3. User A thử Start/Stop, tải History và tạo request mới.
4. Kiểm tra dữ liệu của User B trong cùng thời gian.
5. Admin reactivate User A và xác nhận plan được giữ nguyên.

**Mong đợi:** request mới của User A bị chặn theo trạng thái tài khoản; dữ liệu
User B không bị ảnh hưởng hoặc lộ cho User A; sau reactivate, User A giữ plan
hợp lệ trước đó và có thể tiếp tục sau khi refresh.

### E2E-RX-01 — Xác nhận không có hành vi TX

1. Thực hiện Start/Stop, đổi ngôn ngữ, Live, nghe lại bản dịch và History.
2. Theo dõi cổng audio output, PTT/GPIO và thiết bị vô tuyến test trong suốt
   quá trình.

**Mong đợi:** hệ thống chỉ thu/xử lý RX và phát TTS trên điện thoại; không kích
PTT, không phát RF và không gửi audio bản dịch trở lại thiết bị vô tuyến.

---

## 11. Tiêu chí nghiệm thu

Bản phát hành chỉ được đề xuất nghiệm thu khi:

- Tất cả case về đăng nhập, phân quyền, dữ liệu chéo người dùng, quota, History
  lock, transfer và Audit đều PASS.
- Không có crash, mất dữ liệu, lộ secret hoặc người dùng xem được dữ liệu không
  thuộc quyền.
- Các case vận hành từ xa, không ADC và ranh giới RX/TX đều PASS.
- Các lỗi còn lại đều có ticket, mức độ ưu tiên, người phụ trách và quyết định
  có chấp nhận phát hành hay không.
- Báo cáo test đính kèm phiên bản APK, API, Admin, Station và danh sách case
  PASS/FAIL/BLOCKED/NOT RUN.
