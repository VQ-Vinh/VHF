# Hướng dẫn kiểm thử Android App và Web Admin

> **Chú ý phạm vi:** Tài liệu kiểm thử RX hoàn chỉnh và TX Phase 2.1 từ Android
> đến audio output của Station. Raspberry Pi đã điều khiển GPIO17 PTT; Laptop
> dùng manual PTT. TX chưa sensing channel busy và việc kiểm thử GPIO bằng tải
> giả không được hiểu là đã xác nhận đường truyền RF trên hai máy VHF thật.

## 1. Mục đích

Tài liệu này dành cho đội ngũ tester kiểm thử thủ công PRANA ELEX trên môi
trường staging. Tester không cần đọc source code.

Phạm vi gồm:

- Android App: đăng ký, đăng nhập, ghép Station, điều khiển, RX Live, HTT TX,
  History RX/TX, Account và xử lý mất mạng.
- Web Admin: đăng nhập, Dashboard, Users, Plans, Stations và Audit log.
- Luồng xuyên hệ thống giữa Android App, Cloud, Station và Web Admin.

Không sử dụng tài khoản, audio hoặc Station thật của khách hàng.
Trong toàn bộ tài liệu, Start cho phép Station chạy RX và nhận TX job. Stop dừng
RX và ngăn claim TX mới. Với job đã transmitting, STOP không cắt audio giữa lượt
nhưng ngăn RX resume; watchdog vẫn chịu trách nhiệm nhả PTT an toàn.

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
- Cho phép microphone cho App; có thể thu hồi quyền để kiểm tra lỗi permission.
- Có thể thay đổi múi giờ và cỡ chữ trên điện thoại.
- Chrome hoặc Edge bản mới để kiểm thử Web Admin.
- Một Laptop Station đã provision, có audio input RX và audio output nghe được.
- Một Raspberry Pi/Linux Station dùng ALSA/`arecord`, có GPIO17 nối tải giả/LED
  trước khi nối mạch PTT thật.
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
- Log có cả tiếng Việt, tiếng Anh, tiếng Trung, tiếng Nhật và tiếng Hàn.
- Bộ audio VHF chuẩn gồm giọng rõ, giọng có nhiễu, đoạn im lặng, callsign, số kênh,
  tần số và tọa độ; mỗi mẫu có transcript/bản dịch chuẩn để đối chiếu Gemini.
- Một Station online, một Station offline và một Station có lỗi.
- TX draft ở các trạng thái synthesizing, queued, transmitting, completed và
  failed; có job đã chỉnh translation và job chưa có output WAV.
- Một ngày có nhiều TX job, gồm hai job tạo trong cùng một giây để kiểm tra
  logical filename/sequence.

### 3.4. Kiểm tra trước khi bắt đầu

Ghi lại:

- Phiên bản APK và Station.
- Revision API và Web Admin.
- Múi giờ điện thoại.
- Thời gian bắt đầu test.

Xác nhận màn hình Station báo `API READY` và `ONLINE` trước các case cần thu âm.
Chọn đúng `TX OUTPUT` và đặt âm lượng ở mức an toàn. Khi test Pi, xác nhận tải giả
GPIO trước; chỉ nối VHF/PTT sau khi timing và watchdog đã PASS.
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

### AND-LIVE-07 — Giữ log khi Stop/Start nhiều lần trong ngày

**Các bước**

1. Start Station, tạo ít nhất hai log rồi Stop.
2. Start lại trong cùng ngày và tạo thêm hai log.
3. Lặp lại thêm một lần, sau đó đóng và mở lại màn hình Live.

**Kết quả mong đợi**

- Live chứa log của toàn bộ các lần Start trong ngày, không chỉ session mới nhất.
- Không hiển thị session ID và không thiếu hoặc trùng log.
- Thứ tự log đúng theo timestamp; icon loa của từng log vẫn hoạt động.

### AND-LIVE-08 — Bật/tắt tự động phát audio

**Các bước**

1. Mở Live và xác nhận icon loa cạnh icon History đang bật.
2. Tạo một log mới và nghe audio/bản dịch tự phát.
3. Tắt icon loa rồi tạo thêm hai log.
4. Bật lại icon loa và tạo một log mới khác.
5. Chuyển sang màn hình khác trong lúc App vẫn foreground rồi tạo thêm một log.

**Kết quả mong đợi**

- Khi bật, mỗi log mới chỉ tự phát đúng một lần và đúng thứ tự.
- Khi tắt, âm thanh đang phát dừng, hàng đợi bị xóa và log mới không tự phát.
- Bật lại không phát bù các log sinh ra trong thời gian tắt; chỉ phát log mới tiếp theo.
- Trạng thái icon, tooltip và semantics VI/EN thể hiện rõ đang bật hay tắt.
- Khi đã mở Live của Station, tự phát tiếp tục trong các màn hình khác lúc App foreground.

### AND-LIVE-09 — Nghe lại từng log và không phát lặp

**Các bước**

1. Mở Live đã có sẵn ít nhất 10 log và không thao tác trong ba vòng polling.
2. Bấm icon loa trên một log; khi đang phát, bấm loa của log khác.
3. Stop/Start Station, chuyển màn hình rồi quay lại Live.
4. Đưa App xuống background trong lúc đang phát, chờ có log mới rồi foreground lại.
5. Để App foreground thêm ba vòng polling mà không tạo log mới.

**Kết quả mong đợi**

- Snapshot ban đầu và polling lặp không tự phát 10 log cũ.
- Bấm loa phát ngay đúng nội dung log; log thứ hai ngắt log thứ nhất.
- Stop/Start, rebuild, đổi màn hình và resume không làm log cũ tự phát lại.
- Khi background, âm thanh dừng và log phát sinh trong nền bị bỏ qua khi resume.
- Sau resume, chỉ log thực sự mới phát một lần; không có audio tự phát ngẫu nhiên.

### AND-LIVE-10 — Ngôn ngữ và dữ liệu giọng đọc Android

**Các bước**

1. Tạo lần lượt bản dịch đích Việt, Anh, Trung, Nhật và Hàn.
2. Nghe tự động và bấm nghe lại từng log.
3. Trên thiết bị test, gỡ hoặc tắt voice của một ngôn ngữ rồi thử lại.

**Kết quả mong đợi**

- App chọn locale tương ứng và phát đúng ngôn ngữ khi thiết bị có voice phù hợp.
- Nếu ngôn ngữ nguồn trùng ngôn ngữ đích, App ưu tiên source audio; nếu tải source
  audio lỗi thì chuyển sang TTS transcript.
- Thiếu voice không làm App crash; App cảnh báo thân thiện và hướng dẫn cài dữ liệu
  Text-to-Speech, không hiển thị exception nội bộ.

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

## 7. Android App — TX Phase 2.1

### AND-TX-01 — START gate, offline và command pending

**Các bước**

1. Khi Station đang STOP nhưng online, thử giữ HTT.
2. Gửi lệnh START và thử HTT khi lệnh còn pending.
3. Chờ START apply rồi giữ/nhả HTT để tạo draft.
4. Đưa Station offline và thử lại.
5. Dùng công cụ API staging thử create draft và confirm khi Station STOP.

**Kết quả mong đợi**

- Khi STOP, HTT disabled và hiển thị yêu cầu START Station.
- Khi command pending hoặc offline, App không bắt đầu recording.
- Sau khi START apply, recording và xử lý draft hoạt động bình thường.
- API từ chối cả create và confirm khi desired state không running.
- Không tạo source WAV, draft hoặc usage sai cho request bị từ chối.

### AND-TX-02 — Quyền microphone, hold/release và giới hạn recording

**Các bước**

1. Thu hồi quyền microphone, giữ HTT và lần lượt từ chối/cấp quyền.
2. Giữ HTT khoảng 2 giây rồi nhả; quan sát timer và trạng thái UI.
3. Chạm rất nhanh để tạo đoạn ngắn dưới ngưỡng cho phép.
4. Giữ đến hard limit 60 giây trên bản build/instrumentation phù hợp.
5. Trong lúc recording, thử đổi TX language và nhấn HTT lần hai.

**Kết quả mong đợi**

- Thiếu quyền có thông báo rõ ràng, không crash hoặc tạo file giả.
- Giữ bắt đầu thu, nhả dừng thu đúng một lần và chuyển sang processing.
- Audio quá ngắn bị từ chối an toàn; người dùng có thể thử lại.
- Đến 60 giây App tự kết thúc recording, không tạo audio vượt giới hạn.
- TX language bị khóa và double gesture không tạo hai recording/draft.

### AND-TX-03 — Target snapshot và màn review

**Các bước**

1. Chọn lần lượt các TX language được hỗ trợ và tạo draft.
2. Sau khi enqueue nhưng trước khi có kết quả, đổi cấu hình ngôn ngữ Station bằng
   một client test khác.
3. Mở review, đối chiếu transcript, bản dịch, duration và target language.
4. Thử chỉnh transcript; sau đó chỉnh translation thành nội dung hợp lệ.
5. Xóa trắng translation và nhập nội dung dài hơn 2.000 ký tự.

**Kết quả mong đợi**

- Mỗi draft giữ target tại lúc bắt đầu recording, không bị config mới ghi đè.
- Transcript chỉ đọc; translation chỉnh sửa được.
- Duration và target hiển thị đúng; Unicode của năm ngôn ngữ không lỗi.
- Nút Phát disabled khi nội dung trắng hoặc quá 2.000 ký tự.
- Hủy review xóa draft khỏi UI và draft chưa confirm không vào TX History.

### AND-TX-04 — Confirm, nội dung đã chỉnh và idempotency

**Các bước**

1. Tạo draft, ghi lại translation AI rồi chỉnh thành câu khác có từ “kênh 18”.
2. Bấm Phát và theo dõi synthesizing → queued.
3. Dùng công cụ test gửi lại confirm cùng nội dung/idempotency context.
4. Gửi lại confirm với nội dung khác sau khi draft đã rời review.
5. Nghe output WAV tại Station.

**Kết quả mong đợi**

- Metadata giữ `translation_original`, lưu nội dung cuối ở `translation` và đánh
  dấu edited.
- TTS đọc đúng nội dung đã chỉnh, không đọc bản AI cũ.
- Output có khoảng lặng ngắn rồi clip “Over” tiếng Anh ở cuối.
- Confirm lặp cùng nội dung không tạo WAV/job thứ hai.
- Confirm lặp với nội dung khác bị từ chối và không thay đổi job đã tạo.

### AND-TX-05 — Queue, claim và trạng thái trên App

**Các bước**

1. Confirm một draft và theo dõi queued trên App.
2. STOP Station trước khi worker claim; chờ qua nhiều vòng polling.
3. START lại và chờ Station claim job.
4. Quan sát claimed/transmitting/completed trên App và heartbeat/Admin detail.
5. Mô phỏng hai worker claim đồng thời trên staging test.

**Kết quả mong đợi**

- Queued job chờ khi Station STOP, không bị mất hoặc phát âm thanh.
- START lại cho phép đúng một worker claim job.
- App hội tụ đúng trạng thái, không cho double-submit trong terminal transition.
- Chỉ một playback xảy ra và job completed đúng một lần.

### AND-TX-06 — Half-duplex RX/TX và PTT

**Các bước**

1. START Station và xác nhận RX đang tạo Live result.
2. Gửi một TX job có output đủ dài để quan sát.
3. Theo dõi RX capture, audio output và GPIO/PTT trong lúc TX transmitting.
4. Lặp lại, nhưng bấm STOP khi TX đã transmitting.
5. Lặp lại với thay đổi input/output setting trong lúc TX.

**Kết quả mong đợi**

- Station pause capture RX trước khi kích PTT nhưng cho phép segment RX đã gửi
  trước đó hoàn tất xử lý Gemini.
- Trên Pi, GPIO HIGH trong key-up 400 ms, playback và tail 300 ms; sau đó LOW.
- Trong lúc TX, desired-state loop không tự start RX.
- TX kết thúc khi người dùng STOP giữa lượt, nhưng RX không resume.
- Nếu vẫn running, RX chỉ resume sau khi playback kết thúc.
- Cấu hình mới nhất được tôn trọng sau TX; không chạy đồng thời capture/playback.

### AND-TX-07 — Lỗi output, retry thủ công và chống replay

**Các bước**

1. Mô phỏng lỗi TTS và lỗi archive khi confirm.
2. Mô phỏng output device bị tháo trước claim và lỗi playback sau claim.
3. Theo dõi trong ít nhất năm vòng polling sau mỗi lỗi.
4. Bấm retry thủ công đúng một lần và khôi phục điều kiện gây lỗi.
5. Stop/Start Station và khởi động lại process sau khi job failed.

**Kết quả mong đợi**

- Mỗi lỗi chuyển job sang failed, lưu mã lỗi và không đánh dấu completed.
- TTS/archive lỗi giải phóng active slot và không dùng output cũ.
- Failed job không tự replay qua polling, Stop/Start hoặc restart process.
- Retry tạo attempt mới liên kết job trước, giữ logical filename và chỉ phát sau
  thao tác rõ ràng của người dùng.

### AND-TX-07A — PTT unavailable và watchdog playback

1. Khởi động Raspberry Pi với GPIO17 bị chiếm hoặc driver GPIO không khởi tạo được.
2. Xác nhận RX/heartbeat vẫn hoạt động và App hiển thị không thể điều khiển PTT.
3. Khôi phục GPIO, restart Station và gửi một TX job bằng tải giả.
4. Làm player treo có chủ đích, theo dõi GPIO và trạng thái job trong hơn 122 giây.

**Kết quả mong đợi:** Station lỗi GPIO không claim TX và không fallback phát audio
âm thầm; heartbeat báo `ptt_mode`, `ptt_ready`, `ptt_error`. Khi player treo,
watchdog hạ GPIO, job nhận `TX_PLAYBACK_TIMEOUT`, không tự replay và chỉ cho retry
thủ công khi Station online/running/PTT ready.

### AND-TX-08 — Layout dock và accessibility

**Các bước**

1. Mở Live ở 360×800, 412×915 và text scale 1.3.
2. Kiểm tra cụm trạng thái, HTT trung tâm và TX language.
3. Mở menu ngôn ngữ ở idle và thử mở khi recording/processing.
4. Dùng TalkBack đọc nút HTT, trạng thái và TX language.

**Kết quả mong đợi**

- Dock không overflow; HTT nằm đúng trung tâm.
- TX language/chevron căn đều, touch target mở được toàn bộ hàng.
- Menu đủ năm ngôn ngữ, có check ở ngôn ngữ hiện tại và bị khóa ngoài idle.
- TalkBack đọc đúng enabled/disabled/recording và lý do chưa thể TX.

---

## 8. Android App — History RX/TX và Account

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

### AND-HIS-05 — Tìm kiếm và trình bày log

**Các bước**

1. Tìm một từ trong transcript và một từ trong bản dịch.
2. Xóa từ khóa và cuộn qua các log ngắn, dài, có lỗi và nhiều ngôn ngữ.
3. So sánh thẻ log History với thẻ log ngoài Live.

**Kết quả mong đợi**

- Tìm kiếm áp dụng cho toàn bộ log trong ngày.
- Log trình bày nhất quán với Live: transcript, bản dịch, thời gian và trạng thái
  dễ đọc; nội dung dài tự xuống dòng, không bị cắt hoặc tràn màn hình.
- Màn hình không có nút TXT, CSV, export hoặc **Ẩn khỏi màn hình**.
- History không tự phát audio và không làm thay đổi hàng đợi phát của Live.

### AND-HIS-06 — Làm mới và trạng thái rỗng/lỗi

**Các bước**

1. Mở Station chưa có lịch sử.
2. Mở Station có lịch sử rồi ngắt mạng trong lúc tải chi tiết ngày.
3. Khôi phục mạng và thử lại.

**Kết quả mong đợi**

- Trạng thái rỗng, loading và lỗi đều rõ ràng, song ngữ và không làm App crash.
- Thử lại sau khi có mạng tải đúng danh sách, không nhân đôi log.
- Không lộ URL nội bộ, token, stack trace hoặc exception SDK.

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

### AND-HIS-08 — Chuyển tab RX/TX và giữ trạng thái điều hướng

**Các bước**

1. Mở History mới và ghi nhận tab mặc định.
2. Chuyển TX, mở một ngày rồi quay lại danh sách ngày.
3. Đóng History, mở lại từ nút History hiện tại.
4. Chuyển tab nhanh nhiều lần trong lúc loading.

**Kết quả mong đợi**

- History mới luôn mặc định RX; không có nút TX History riêng ở dock.
- Khi đi vào/ra chi tiết ngày, tab TX vẫn được giữ.
- Đóng và mở mới reset về RX.
- RX/TX không tải nhầm endpoint, trộn dữ liệu hoặc nhân đôi item.

### AND-HIS-09 — TX History, search và output playback

**Các bước**

1. Mở ngày có các trạng thái synthesizing, queued, transmitting, completed và failed.
2. Tìm theo transcript và nội dung cuối đã phát.
3. Đối chiếu status, source/target language, edited flag và attempt.
4. Bấm loa ở completed job; thử bấm loa ở job chưa có output.
5. Kiểm tra draft đã hủy trước confirm.

**Kết quả mong đợi**

- Chỉ job đã confirm xuất hiện; draft cancelled trước confirm bị loại.
- Search áp dụng cho transcript và translation cuối.
- Card hiển thị đúng metadata, nội dung dài không overflow.
- Nút loa stream đúng output WAV và disabled khi output chưa tồn tại.
- History không trả hoặc hiển thị Cloud object path.

### AND-HIS-10 — Entitlement, timezone và ownership của TX History

**Các bước**

1. Kiểm tra cùng ngày TX bằng User Free và User Pro theo delay đã cấu hình.
2. Đổi timezone điện thoại qua mốc nửa đêm và tải lại danh sách ngày.
3. Dùng User B thử gọi days/jobs/audio của Station User A.
4. Thử station/date/job ID sai và TX job legacy thiếu output.

**Kết quả mong đợi**

- RX và TX dùng cùng `history_unlock_delay_days`.
- Grouping ngày theo timezone client, không làm đổi timestamp gốc.
- User khác và identifier sai bị từ chối, không lộ sự tồn tại/object path.
- Job legacy hoặc thiếu output trả trạng thái audio unavailable an toàn.

---

## 9. Android App — giao diện và lỗi mạng

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

### OPS-RX-02 — Xử lý Gemini và chất lượng bản dịch VHF

**Các bước**

1. Lần lượt phát bộ audio chuẩn: rõ, nhiễu, im lặng, callsign, số kênh, tần số,
   tọa độ và các ngôn ngữ đã chuẩn bị.
2. Chọn từng ngôn ngữ đích được App hỗ trợ và ghi lại transcript/bản dịch.
3. Gửi một audio vượt giới hạn cho phép và mô phỏng Gemini timeout trên staging.
4. Đối chiếu request ID, quota và kết quả sau khi Retry.

**Kết quả mong đợi**

- Hệ thống dùng Gemini đã cấu hình để nhận dạng, khôi phục và dịch trong một lượt
  xử lý; không gọi DeepSeek hoặc pipeline STT riêng.
- Không tự bịa nội dung khi audio không rõ; số, callsign, tần số và tọa độ được bảo
  toàn hoặc đánh dấu không chắc chắn theo quy ước sản phẩm.
- Bản dịch đúng ngôn ngữ đích; khi nguồn trùng đích, bản dịch khớp transcript đã
  khôi phục.
- Audio không hợp lệ, timeout và lỗi model có thông báo an toàn, không trừ quota
  hai lần và Retry không tạo log trùng.

### OPS-RX-03 — Lưu local, GCS và dọn dữ liệu 14 ngày

**Các bước**

1. Tạo một RX result mới và ghi lại tên WAV/JSON local.
2. Kiểm tra `VHF_Storage/RX/audio` và `VHF_Storage/RX/results`.
3. Kiểm tra vùng RX tương ứng trong Cloud Storage bằng công cụ staging.
4. Đối chiếu nhánh `RX/audio/YYYY/MM/DD` và `RX/result/YYYY/MM/DD`.
5. Chạy lại cùng request để kiểm tra idempotency.
6. Chuẩn bị file local quá 14 ngày và file chưa đủ 14 ngày, sau đó khởi động lại
   bằng `enable_station_api.bat` và chờ chu kỳ dọn dữ liệu.

**Kết quả mong đợi**

- Dữ liệu RX mới nằm dưới `VHF_Storage/RX`; log/PID/runtime nằm ngoài vùng dữ
  liệu nghiệp vụ.
- WAV và JSON có cùng stem theo định dạng `YYYYMMDD_HHMMSS_NNNN`; JSON hợp lệ.
- Object Cloud nằm đúng owner/Station, đúng ngày, tách RX audio/result và giữ
  đúng tên local; API không trả object path cho App.
- Retry cùng request không tạo object trùng; audio mới và audio lịch sử vẫn nghe được.
- Chỉ dữ liệu local quá hạn 14 ngày bị xóa; dữ liệu còn hạn không bị ảnh hưởng.

### OPS-TX-01 — Lưu source/output/result và logical filename

**Các bước**

1. Tạo hai TX job trong cùng một giây và hoàn tất playback.
2. Kiểm tra `VHF_Storage/TX/source`, `output` và `results` theo ngày.
3. Đối chiếu ba file của từng job và metadata attempt/translation.
4. Kiểm tra vùng TX tương ứng trên Cloud bằng công cụ staging.
5. Retry một failed job và kiểm tra tên file/attempt.

**Kết quả mong đợi**

- Tên theo `YYYYMMDD_HHMMSS_NNNN`; hai job cùng giây có sequence khác nhau.
- Source WAV, output WAV và JSON của một job có cùng stem.
- TX sequence độc lập RX; retry giữ logical filename và tăng attempt.
- Cloud tách `TX/source`, `TX/output`, `TX/result` và giữ cùng basename.
- Layout UUID cũ vẫn đọc được; không tự migration hoặc xóa archive cũ.

### OPS-TX-02 — Output device và heartbeat TX

**Các bước**

1. Mở Station Settings và liệt kê input/output devices.
2. Chọn một device không có output channel nếu công cụ test cho phép.
3. Chọn output hợp lệ, lưu desired state và gửi TX.
4. Trong claimed/transmitting, đối chiếu heartbeat và Station detail.
5. Tháo output device rồi thử TX mới.

**Kết quả mong đợi**

- TX OUTPUT chỉ cho chọn device có `output_channels > 0` và lưu độc lập RX input.
- Heartbeat báo đúng `tx_state`, job ID, active TX output device và lỗi TX.
- Không tái sử dụng `capture_state` để biểu diễn TX.
- Device mất/không hợp lệ làm job failed, không fallback âm thầm sang output sai.

---

## 10. Web Admin

### ADM-SEC-01 — Quyền truy cập

**Các bước**

1. Mở Web Admin trong cửa sổ ẩn danh khi chưa đăng nhập.
2. Đăng nhập bằng Non-admin.
3. Đăng nhập bằng Admin.
4. Đóng cửa sổ, mở lại sau khi phiên IAP hết hạn và thử truy cập trực tiếp một URL
   chi tiết đã lưu.

**Kết quả mong đợi**

- Người chưa đăng nhập được yêu cầu đăng nhập.
- Non-admin nhận trang 403 và không thấy dữ liệu quản trị.
- Admin truy cập Dashboard bình thường.
- Khi không còn phiên hợp lệ, mọi URL đều yêu cầu xác thực lại; nút Back hoặc cache
  trình duyệt không làm lộ nội dung Admin trước đó.

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

### ADM-STA-03 — Release Station để ghép lại

**Các bước**

1. Mở User detail có Station inactive/locked và thử quét lại tem QR trên Android.
2. Bấm Release trên Web Admin; lần đầu hủy dialog, lần sau xác nhận.
3. Kiểm tra Audit rồi dùng User B quét lại đúng tem QR.

**Kết quả mong đợi**

- Trước khi release, App báo Station bị khóa và không cho ghép lại.
- Hủy dialog không thay đổi dữ liệu; xác nhận release mở đúng Station, không ảnh
  hưởng Station khác.
- User B ghép lại thành công nhưng không được xem lịch sử riêng của owner cũ.
- Audit ghi operator, Station, owner trước/sau, request ID và timestamp.

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
- Sidebar dùng đúng logo PRANA ELEX; avatar giữ màu/ảnh từ danh tính Google thay vì
  bị thay bằng màu mặc định không nhất quán.
- Trang 403/404/409/422/500 song ngữ, đúng mã lỗi và không lộ exception,
  stack trace hay secret.

---

## 11. Kiểm thử xuyên hệ thống

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

### E2E-06 — Một RX result xuyên suốt toàn hệ thống

1. Android Start RX và phát một mẫu VHF có request ID xác định.
2. Theo dõi Station upload, Gemini xử lý, Live hiển thị và tự phát bản dịch.
3. Stop/Start lại trong ngày, mở History khi entitlement cho phép.
4. Đối chiếu local, Firestore/GCS bằng công cụ staging và usage trên Account/Admin.

**Mong đợi:** chỉ có một result cho request ID; transcript/bản dịch giống nhau ở
Live và History; log vẫn còn sau Stop/Start; usage chỉ tăng một lần; WAV/JSON local
và GCS cùng tên, đúng Station/ngày; không có audio tự phát lặp ngoài lần phát mới.

### E2E-07 — Một TX job xuyên suốt toàn hệ thống

1. Android START Station, chọn TX language và thu câu “Vui lòng chuyển qua kênh
   18 VHF” bằng HTT.
2. Đối chiếu transcript/translation, chỉnh nội dung rồi bấm Phát.
3. Theo dõi synthesizing, archive, queued, Station claim và playback.
4. Nghe nội dung cuối và “Over” trên output Laptop; chờ completed.
5. Mở History TX và đối chiếu local/Cloud metadata bằng công cụ staging.

**Mong đợi:** source chỉ upload một lần; nội dung chỉnh được TTS đúng; output có
“Over”; RX dừng trước playback và resume sau đó; App đạt completed; History có
đúng một job với edited flag/attempt; source/output/result cùng logical stem và
không lộ Cloud path.

### E2E-08 — Admin STOP trong vòng đời TX

1. User A confirm TX và để job queued, sau đó Admin gửi STOP.
2. Xác nhận job chưa claim trong khi Station STOP.
3. START lại, chờ job transmitting rồi Admin gửi STOP lần nữa.
4. Theo dõi playback, RX state và Audit.

**Mong đợi:** queued job chờ đến lần START tiếp theo; transmitting job phát hết
nhưng RX không resume; Android/Station/Admin cuối cùng cùng hội tụ về stopped;
Audit chỉ ghi thao tác Admin, không ghi completed giả hoặc replay job.

### E2E-TX-BOUNDARY-01 — Xác nhận ranh giới GPIO/PTT và RF

1. Trên Laptop, chạy đầy đủ TX và xác nhận `ptt_mode=manual`.
2. Trên Pi, nối GPIO17 vào tải giả, chạy TX bình thường và test player treo.
3. Sau khi timing/watchdog PASS mới nối mạch cách ly PTT và VHF theo phê duyệt.

**Mong đợi:** Laptop không giả vờ có GPIO; Pi không claim nếu GPIO unavailable.
GPIO chỉ HIGH trong cửa sổ TX và luôn về LOW khi lỗi/shutdown/watchdog. Kết quả
trên tải giả không được ghi nhận là phát RF thành công nếu chưa kiểm thử hai VHF.

---

## 12. Tiêu chí nghiệm thu

Bản phát hành chỉ được đề xuất nghiệm thu khi:

- Tất cả case về đăng nhập, phân quyền, dữ liệu chéo người dùng, quota, History
  lock, transfer và Audit đều PASS.
- Không có crash, mất dữ liệu, lộ secret hoặc người dùng xem được dữ liệu không
  thuộc quyền.
- Các case vận hành từ xa, không ADC và ranh giới RX/TX đều PASS.
- Toàn bộ case TX START gate, recording/review, TTS + “Over”, queue, interlock,
  retry thủ công, lưu trữ và History TX đều PASS trên Laptop Station.
- Các case Gemini, tự phát/nghe lại audio, lưu local/GCS và dọn dữ liệu 14 ngày đều
  PASS trên ít nhất một Station Windows và một Station Raspberry Pi/Linux.
- Không có TX job tự replay; GPIO17 PTT và watchdog PASS trên tải giả. Phát RF chỉ
  được đánh dấu PASS khi có biên bản kiểm thử hai VHF thật.
- Các lỗi còn lại đều có ticket, mức độ ưu tiên, người phụ trách và quyết định
  có chấp nhận phát hành hay không.
- Báo cáo test đính kèm phiên bản APK, API, Admin, Station và danh sách case
  PASS/FAIL/BLOCKED/NOT RUN.
