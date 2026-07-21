# Hướng dẫn kiểm thử E2E PRANA ELEX trên Staging

## 1. Mục đích

Tài liệu này hướng dẫn đội QA kiểm thử toàn bộ hành trình PRANA ELEX, từ cài đặt ứng dụng Windows đến đăng ký tài khoản, tự động nhận gói Free, dịch audio, quản lý quota, thiết bị, nâng cấp và gỡ cài đặt.

Phạm vi chính:

- Ứng dụng Windows 10/11 x64.
- PRANA API và Firebase Authentication trên staging.
- Web Admin được bảo vệ bằng Google Cloud IAP.
- Kiểm thử bổ sung cho Raspberry Pi nằm ở Phụ lục A.

Không sử dụng tài khoản, email hoặc dữ liệu khách hàng thật trong quá trình kiểm thử.

## 2. Thông tin môi trường

| Hạng mục | Giá trị |
|---|---|
| Môi trường | Staging |
| Windows installer | `PRANA_ELEX_Setup_1.1.0_x64.exe` |
| PRANA API | <https://prana-api-owuilj5d4a-uc.a.run.app> |
| PRANA API revision tại thời điểm viết | `prana-api-00011-8jc` (`1.1.0-staging.9`) |
| Web Admin | <https://prana-admin-owuilj5d4a-uc.a.run.app> |
| Web Admin revision tại thời điểm viết | `prana-admin-00004-mvg` |
| Project staging | `prana-elex-staging-2816` |
| Trình duyệt khuyến nghị | Chrome hoặc Edge bản mới nhất |

Trước mỗi đợt test, QA Lead phải cập nhật lại phiên bản installer, revision PRANA API,
revision Web Admin và ngày chạy test nếu chúng đã thay đổi.

### Thông tin test run

| Trường | Giá trị cần điền |
|---|---|
| Test run ID | |
| Ngày kiểm thử | |
| Người kiểm thử | |
| Phiên bản app | |
| Tên file installer | |
| SHA-256 installer | |
| Windows edition/build | |
| Máy hoặc VM | |
| Email user test | |
| Email admin test | |
| Kết quả tổng thể | `PASS` / `FAIL` / `BLOCKED` |

## 3. Vai trò cần chuẩn bị

### 3.1. Tester ứng dụng

Tester ứng dụng cần:

- Một email thật có thể nhận email xác minh và đặt lại mật khẩu.
- Một máy Windows 10/11 x64 hoặc VM sạch.
- Quyền chạy installer và quyền Administrator nếu test chế độ cài cho mọi người dùng.
- Loa, microphone hoặc nguồn audio loopback hoạt động.
- Internet ổn định, đồng thời có khả năng ngắt mạng để test offline.

### 3.2. Tester Web Admin

Tester Web Admin cần:

- Tài khoản Google đã được cấp quyền IAP và nằm trong allowlist Admin.
- Tài khoản hiện đang sử dụng: `technical@samaser.com.vn`.
- Quyền xem catalog plan, đổi trạng thái và quản lý thiết bị trên staging.

### 3.3. Dữ liệu test

Chuẩn bị tối thiểu:

- Một đoạn tiếng Anh rõ tiếng dài 10 đến 14 giây.
- Một đoạn tiếng Việt rõ tiếng dài 10 đến 14 giây.
- Một đoạn giọng nói liên tục dài khoảng 31 giây để test chia segment 15 giây.
- Một đoạn chỉ có im lặng hoặc nhiễu nền.
- Một email user test mới chưa đăng ký Firebase.
- Một tài khoản Google nằm trong danh sách Test users của OAuth consent screen.
- Một tài khoản Email/Password có cùng email Google để kiểm thử liên kết provider.
- Nếu test giới hạn thiết bị: ba máy hoặc ba Windows user profile độc lập.

Không dùng audio có thông tin cá nhân, bí mật kinh doanh hoặc nội dung của khách hàng.

## 4. Quy tắc ghi nhận kết quả

Mỗi test case phải lưu:

- Trạng thái `PASS`, `FAIL`, `BLOCKED` hoặc `NOT RUN`.
- Ảnh chụp màn hình ở bước quan trọng.
- Thời gian xảy ra lỗi theo múi giờ máy test.
- Email test, nhưng không ghi mật khẩu hoặc token.
- Nội dung Developer Console khi có lỗi ứng dụng.
- URL trang Web Admin và ảnh trạng thái user khi lỗi liên quan subscription hoặc device.

Không chụp hoặc gửi:

- Mật khẩu.
- Firebase token.
- Windows Credential Manager secret.
- Private key thiết bị.
- Credential hoặc JSON key Google Cloud.

## 5. Chuẩn bị máy Windows sạch

### TC-PRE-01: Chuẩn bị môi trường

1. Ưu tiên tạo VM snapshot hoặc Windows user profile mới.
2. Xác nhận chưa có tiến trình `PRANA_ELEX.exe` chạy trong Task Manager.
3. Xác nhận không có thư mục cài đặt PRANA ELEX từ test run trước.
4. Nếu tái sử dụng máy, mở app cũ và thực hiện **Đăng xuất** trước khi gỡ cài đặt.
5. Không cài Google Cloud CLI, service-account JSON hoặc biến `GOOGLE_APPLICATION_CREDENTIALS` trên máy user test.
6. Sao chép installer vào máy test.
7. Tính SHA-256:

   ```powershell
   Get-FileHash .\PRANA_ELEX_Setup_1.1.0_x64.exe -Algorithm SHA256
   ```

8. Ghi hash vào bảng thông tin test run và đối chiếu với hash do đội phát hành cung cấp.

**Kết quả mong đợi:**

- Hash trùng với bản phát hành.
- Máy user không cần tài khoản Google Cloud hoặc JSON key.
- Không còn tiến trình app cũ ảnh hưởng installer.

## 6. Cài đặt ứng dụng Windows

### TC-INST-01: Cài mới cho người dùng hiện tại

1. Mở `PRANA_ELEX_Setup_1.1.0_x64.exe`.
2. Nếu Windows SmartScreen hoặc antivirus hiển thị cảnh báo, chụp lại màn hình.
3. Đối chiếu trạng thái chữ ký số với yêu cầu của release. Bản staging chưa ký có thể hiện cảnh báo; bản production yêu cầu ký số thì thiếu chữ ký là lỗi phát hành.
4. Chọn ngôn ngữ **Tiếng Việt**.
5. Tại trang Welcome, xác nhận:
   - Tên ứng dụng là `PRANA ELEX`.
   - Phiên bản đúng với release đang test.
   - Logo và nội dung không bị méo hoặc tràn chữ.
6. Chọn **Install for me** hoặc chế độ tương đương chỉ dành cho người dùng hiện tại.
7. Tại trang **Vị trí cài đặt**, xác nhận có hai vùng riêng biệt:
   - **Thư mục cài ứng dụng**.
   - **Thư mục dữ liệu**.
8. Chọn ví dụ:
   - Application folder: `%LOCALAPPDATA%\Programs\PRANA ELEX`.
   - Data folder: `%USERPROFILE%\Documents\PRANA ELEX Data`.
9. Không đặt Data folder bên trong Application folder.
10. Nhấn **Tiếp theo**.
11. Chọn tạo Desktop shortcut.
12. Để Autostart tắt trong lần test đầu tiên.
13. Tại trang Ready to Install, đối chiếu lại:
   - Application folder.
   - Data folder.
   - Install scope là current user.
   - Desktop shortcut và Autostart đúng lựa chọn.
14. Nhấn **Cài đặt**.
15. Tại trang Finished, giữ tùy chọn mở PRANA ELEX và hoàn tất.

**Kết quả mong đợi:**

- Cài đặt hoàn tất không lỗi.
- Application folder và Data folder được tạo đúng vị trí.
- Có shortcut nếu đã chọn.
- App mở được bằng user hiện tại.
- Không có cửa sổ chọn Data folder lần thứ hai trong app Windows đóng gói.

### TC-INST-02: Kiểm tra validation đường dẫn

Chạy lại installer cho từng trường hợp sau, nhưng hủy trước khi cài thật:

1. Để trống Application folder.
2. Để trống Data folder.
3. Chọn root ổ đĩa như `D:\` làm Data folder.
4. Chọn Data folder giống Application folder.
5. Chọn Data folder nằm bên trong Application folder.
6. Chọn Application folder nằm bên trong Data folder.
7. Chọn một vị trí mà user không có quyền ghi.

**Kết quả mong đợi:**

- Installer chặn từng trường hợp không hợp lệ.
- Thông báo lỗi đúng ngôn ngữ đang chọn.
- Installer không clean hoặc xóa dữ liệu tại đường dẫn bị từ chối.

### TC-INST-03: Cài cho mọi người dùng

Thực hiện trên máy hoặc snapshot riêng:

1. Mở installer.
2. Chọn **Install for all users**.
3. Chấp nhận UAC bằng tài khoản Administrator.
4. Xác nhận đường dẫn mặc định:
   - Application folder thuộc `Program Files`.
   - Data folder thuộc `ProgramData\PRANA ELEX\Data`.
5. Hoàn tất cài đặt.
6. Đăng nhập bằng Windows user khác và mở app.

**Kết quả mong đợi:**

- App chạy được cho user khác.
- Data folder dùng chung có quyền ghi phù hợp.
- Settings máy trỏ đúng Data folder đã chọn.

## 7. Kiểm tra màn hình đăng nhập và đăng ký

### TC-AUTH-01: First launch

1. Mở PRANA ELEX.
2. Quan sát cửa sổ chính.
3. Chuyển EN/VI bằng nút ngôn ngữ.
4. Kiểm tra trang **Đăng nhập** và **Tạo tài khoản**.

**Kết quả mong đợi:**

- Login/Register nằm trong cửa sổ chính, không phải dialog rời.
- Giao diện không bị cắt chữ ở DPI 100%, 125%, 150% và 200%.
- App Windows không hỏi lại Data folder.
- Không có trường chọn JSON key hoặc Google credential.

### TC-AUTH-02: Validation mật khẩu đăng ký

1. Chọn tab **Tạo tài khoản**.
2. Nhập email test hợp lệ.
3. Lần lượt thử mật khẩu thiếu từng điều kiện:
   - Dưới 6 ký tự.
   - Không có chữ cái.
   - Không có chữ viết hoa.
   - Không có chữ số.
   - Không có ký tự đặc biệt.
   - Chỉ dùng khoảng trắng làm ký tự đặc biệt.
4. Quan sát checklist dưới ô mật khẩu.
5. Thử mật khẩu đáp ứng đủ yêu cầu, ví dụ dành riêng cho staging: `Prana#123`.

**Kết quả mong đợi:**

- Checklist cập nhật ngay khi nhập.
- Nút **Tạo tài khoản** bị vô hiệu khi chưa đủ điều kiện.
- Khoảng trắng không được tính là ký tự đặc biệt.
- Không gửi request tạo tài khoản khi mật khẩu chưa hợp lệ.
- Không ghi mật khẩu ví dụ vào báo cáo test thực tế.

### TC-AUTH-03: Tạo tài khoản và xác minh email

1. Nhập email test mới và mật khẩu hợp lệ.
2. Nhấn **Tạo tài khoản**.
3. Kiểm tra hộp thư đến và Spam.
4. Trước khi xác minh, quay lại app và nhấn **Làm mới**.
5. Nhấn **Gửi lại email xác minh** một lần.
6. Mở liên kết xác minh trong email.
7. Quay lại app và nhấn **Làm mới**.

**Kết quả mong đợi:**

- Sau đăng ký, app chuyển đến Trung tâm tài khoản ở trạng thái restricted.
- Trước xác minh, app hiển thị yêu cầu xác minh email và không cho dịch.
- Resend gửi lại email nhưng không tạo tài khoản mới.
- Sau xác minh, tài khoản tự chuyển sang **Hoạt động** với gói **Free**.
- Pipeline có thể chạy ngay, không cần Admin kích hoạt.

### TC-AUTH-04: Đăng nhập sai và quên mật khẩu

1. Đăng xuất nếu đang có session.
2. Thử đăng nhập bằng mật khẩu sai.
3. Xác nhận app hiển thị lỗi trong trang, không đóng app.
4. Nhập email test và nhấn **Quên mật khẩu**.
5. Thử lại với một email không tồn tại.

**Kết quả mong đợi:**

- Đăng nhập sai không tạo session.
- Luồng quên mật khẩu luôn trả thông báo trung tính.
- Email tồn tại nhận được thư đặt lại mật khẩu.
- UI không tiết lộ email nào đã hoặc chưa đăng ký.

### TC-AUTH-05: Đăng ký và đăng nhập bằng Google

1. Đăng xuất khỏi app và xác nhận trang xác thực có nút **Tiếp tục với Google**.
2. Nhấn nút Google; xác nhận trình duyệt hệ thống mở màn hình chọn tài khoản.
3. Chọn một tài khoản trong danh sách Test users của consent screen.
4. Quay lại app sau khi trình duyệt báo hoàn tất.
5. Mở Account Center và xác nhận gói Free, usage ngày và thiết bị.
6. Thử dịch audio.
7. Đăng xuất, đăng nhập lại bằng Google và khởi động lại app.

**Kết quả mong đợi:**

- Callback dùng địa chỉ `127.0.0.1` và không hiển thị token trong URL/nội dung trang.
- Tài khoản mới xuất hiện một lần ở trạng thái active, email đã verified và plan là Free.
- Subscription, device và quota hoạt động giống Email/Password mà không cần Admin duyệt.
- Mỗi lần bấm Google đều hiện màn hình chọn tài khoản.
- App tự đăng nhập sau restart bằng Firebase session; không lưu Google token.

### TC-AUTH-06: Liên kết Google với tài khoản Email/Password

1. Đăng nhập bằng tài khoản Email/Password đã có subscription và usage.
2. Ghi lại email, UID trong Admin, plan, usage, thiết bị và Data folder.
3. Mở Account Center, chọn **Liên kết tài khoản Google**.
4. Trước tiên chọn một Google email khác; xác nhận liên kết bị từ chối.
5. Thử lại và chọn Google email trùng chính xác với tài khoản hiện tại.
6. Đăng xuất rồi đăng nhập bằng Google.
7. Đối chiếu lại UID, plan, usage, thiết bị và dữ liệu local.

**Kết quả mong đợi:**

- Email khác bị chặn và không tạo Firebase user trùng.
- Email đúng được hiển thị là đã liên kết; Email/Password vẫn sử dụng được.
- UID, subscription, quota, device và Data folder không thay đổi.
- App không cung cấp thao tác unlink trong phiên bản này.

## 8. Kiểm thử Web Admin

### TC-ADM-01: Đăng nhập và kiểm tra quyền IAP

1. Mở cửa sổ trình duyệt bình thường.
2. Truy cập <https://prana-admin-owuilj5d4a-uc.a.run.app>.
3. Đăng nhập bằng tài khoản Google Admin được cấp quyền.
4. Mở cửa sổ ẩn danh và thử bằng tài khoản Google không được allowlist, nếu QA có tài khoản phù hợp.

**Kết quả mong đợi:**

- Admin hợp lệ vào được Dashboard.
- Email operator hiển thị đúng ở sidebar.
- Tài khoản không được cấp quyền bị từ chối, không xem được dữ liệu user.
- Không có cơ chế đăng nhập Admin bằng tài khoản Firebase của khách hàng.

### TC-ADM-02: Kiểm tra giao diện và ngôn ngữ

1. Chuyển giữa EN và VI ở góc trên.
2. Mở lần lượt:
   - Tổng quan.
   - Người dùng.
   - Gói dịch vụ.
3. Thu nhỏ trình duyệt xuống chiều rộng tablet và mobile.
4. Mở menu mobile, chọn từng trang và nhấn `Escape`.

**Kết quả mong đợi:**

- Ngôn ngữ được giữ khi chuyển trang.
- Sidebar, bảng và form không chồng lấn.
- Bảng rộng cho phép cuộn ngang trên màn hình nhỏ.
- Menu mobile đóng khi chọn trang, nhấn vùng ngoài hoặc nhấn `Escape`.
- Status hiển thị bằng nhãn dễ hiểu, không chỉ hiển thị mã kỹ thuật.

### TC-ADM-03: Kiểm tra Dashboard

1. Mở **Tổng quan**.
2. Kiểm tra bốn chỉ số:
   - Tổng người dùng.
   - Gói đang hoạt động.
   - Chờ kích hoạt.
   - Âm thanh tháng này.
3. Kiểm tra vùng **Cần xử lý**.
4. Kiểm tra **Hoạt động quản trị gần đây**.

**Kết quả mong đợi:**

- User vừa đăng ký xuất hiện trong vùng cần xử lý.
- Audit log hiển thị action, operator và thời gian.
- Không tràn email hoặc timestamp ra ngoài panel.

### TC-ADM-04: Kiểm tra chỉnh sửa thông số gói

1. Mở **Gói dịch vụ**.
2. Kiểm tra ba card Free, Plus và Pro.
3. Ghi lại số phút/ngày hiện tại của Free là `N`.
4. Đổi Free thành `N + 1` phút/ngày rồi nhấn **Lưu gói**.
5. Refresh trang và xác nhận giá trị mới vẫn được giữ.
6. Mở trang Plans trong app và giữ trang này mở.
7. Chờ tối đa 30 giây hoặc nhấn **Refresh**, sau đó xác nhận card Free hiển thị `N + 1`.
8. Quay lại Account Center và xác nhận Daily usage sử dụng giới hạn mới.
9. Đổi Free trở lại `N` phút/ngày và xác nhận app đồng bộ lại.

**Kết quả mong đợi:**

- Chỉ có Free, Plus và Pro; không còn StagingTest.
- Có thể chỉnh tên, phút/ngày, RPM, concurrency, số thiết bị và thứ tự hiển thị.
- Giá trị ngoài khoảng cho phép bị trình duyệt/backend từ chối.
- Thay đổi có hiệu lực ngay và xuất hiện trong audit log.
- Plus hiển thị 60 phút/ngày; Pro hiển thị 180 phút/ngày.
- Plus và Pro có trạng thái Sắp phát hành.

### TC-ADM-05: Tìm và quản lý trạng thái user

1. Mở **Người dùng**.
2. Tìm theo email user test.
3. Kiểm tra bộ lọc trạng thái và plan.
4. Mở trang chi tiết user.
5. Xác nhận:
   - Email đúng.
   - Email verified là Có/Yes.
   - Trạng thái Hoạt động.
   - Plan là `free` và không có ngày hết hạn.
6. Chuyển trạng thái sang Suspended rồi kiểm tra app bị chặn.
7. Chuyển lại Active và kiểm tra tài khoản trở về Free.
8. Quay lại Dashboard và kiểm tra audit log.

**Kết quả mong đợi:**

- User Free hoạt động mà không cần thao tác cấp plan.
- Suspend chặn dịch; Active khôi phục plan Free không hết hạn.
- Audit có action đổi trạng thái với đúng operator.

## 9. Kiểm tra gói tự phục vụ trong app

### TC-APP-01: Nhận Free và mở trang Plans

1. Quay lại PRANA ELEX.
2. Tại Trung tâm tài khoản, nhấn **Làm mới**.
3. Kiểm tra email, xác minh, plan Free và usage hôm nay.
4. Nhấn **Quản lý gói** và kiểm tra ba card.
5. Quay lại màn hình dịch.

**Kết quả mong đợi:**

- Subscription hiển thị **Đang hoạt động**.
- Tổng quota khớp giá trị Free hiện tại trên Web Admin và hiển thị thời điểm reset ngày kế tiếp.
- Free là gói hiện tại; nút Plus và Pro bị vô hiệu hóa với nhãn Sắp phát hành.
- Thiết bị hiện tại xuất hiện với badge **Thiết bị này**.
- App vào được màn hình Translation.

### TC-APP-02: Cấu hình audio và giao diện

1. Mở **Cài đặt** bằng biểu tượng bánh răng.
2. Chuyển giao diện sang Tiếng Việt rồi lưu.
3. Mở lại Settings và chọn:
   - Capture mode `device` để test microphone; hoặc
   - Capture mode `loopback` để thu âm thanh đang phát từ loa.
4. Chọn đúng audio device.
5. Bật hoặc tắt Autostart theo test case.
6. Nhấn **Lưu**.
7. Khởi động lại app để xác nhận lựa chọn được giữ.

**Kết quả mong đợi:**

- Settings chỉ chứa giao diện, audio capture và autostart.
- Subscription và device management nằm trong Trung tâm tài khoản, không nằm trong Settings.
- Ngôn ngữ giao diện đổi ngay và được giữ sau restart.
- Audio device và capture mode được giữ.

## 10. Kiểm thử dịch audio

### TC-TRN-01: Dịch tiếng Anh sang tiếng Việt

1. Chọn ngôn ngữ đầu ra là Tiếng Việt.
2. Nhấn **Bắt đầu**.
3. Chờ trạng thái RX chuyển sang active/listening.
4. Phát hoặc nói đoạn tiếng Anh 10 đến 14 giây.
5. Dừng nói và chờ kết quả.

**Kết quả mong đợi:**

- RX chuyển qua các trạng thái hợp lý: starting, active/listening, receiving.
- Ngôn ngữ đầu vào hiển thị tiếng Anh sau khi segment được xử lý.
- Transcript tiếng Anh và bản dịch tiếng Việt xuất hiện trong feed.
- API status chuyển thành `API OK`.
- Thanh trạng thái dưới không hiển thị Latency.
- Developer Console vẫn có thời gian xử lý kỹ thuật.

Lưu ý: tính năng detect ngôn ngữ sớm bằng request preview đã bị loại bỏ. Ngôn ngữ đầu vào chỉ cần cập nhật khi kết quả segment chính trả về.

### TC-TRN-02: Dịch tiếng Việt sang tiếng Anh

1. Chọn ngôn ngữ đầu ra là English.
2. Phát hoặc nói đoạn tiếng Việt 10 đến 14 giây.
3. Chờ kết quả.

**Kết quả mong đợi:**

- Input language là Tiếng Việt.
- Transcript và bản dịch đúng chiều Việt sang Anh.
- Không xuất hiện request hoặc dòng log detect-language riêng.

### TC-TRN-03: Segment tối đa 15 giây

1. Giữ pipeline đang chạy.
2. Phát đoạn giọng nói liên tục khoảng 31 giây, hạn chế khoảng lặng dài.
3. Quan sát số kết quả và thứ tự câu.
4. Đối chiếu Developer Console.

**Kết quả mong đợi:**

- Audio được tự chia thành các segment tối đa khoảng 15 giây.
- Segment được xử lý tuần tự với sequence tăng dần.
- Không có phần lời nói bị mất hoặc lặp rõ ràng tại ranh giới.
- Phần audio còn lại sau 30 giây được xử lý khi VAD kết thúc lượt nói.
- Người dùng không phải chờ toàn bộ 31 giây mới nhận kết quả đầu tiên.

Số segment thực tế có thể thay đổi nếu file chứa khoảng lặng đủ dài để VAD kết thúc sớm.

### TC-TRN-04: Im lặng và nhiễu nền

1. Chạy pipeline trong môi trường yên lặng ít nhất 15 giây.
2. Phát đoạn chỉ có nhiễu nền nhẹ.

**Kết quả mong đợi:**

- Không tạo hàng loạt bản dịch rỗng.
- Segment quá ngắn bị loại theo VAD.
- App không treo và vẫn tiếp tục listening.

### TC-TRN-05: Kiểm tra dữ liệu local

1. Dừng pipeline.
2. Mở Data folder đã chọn trong installer.
3. Kiểm tra:

   ```text
   <Data folder>\VHF_Storage\audio
   <Data folder>\VHF_Storage\results
   ```

4. Mở một file JSON kết quả bằng editor văn bản.

**Kết quả mong đợi:**

- WAV nằm trong `VHF_Storage\audio`.
- JSON nằm trong `VHF_Storage\results`.
- Không có đoạn dư `accounts\<firebase_uid>` trong đường dẫn.
- JSON chứa transcript, translation, language và metadata liên quan.
- Không có token, mật khẩu, private key hoặc Google credential trong JSON.

### TC-TRN-06: Lịch sử dịch

1. Nhấn biểu tượng lịch sử trên màn hình Translation.
2. Tìm một từ có trong transcript hoặc translation.
3. Kiểm tra nội dung các cột.
4. Test Export vào một thư mục QA.
5. Chỉ test Clear All sau khi đã sao lưu bằng chứng cần thiết.

**Kết quả mong đợi:**

- Lịch sử khớp với kết quả vừa dịch.
- Search lọc đúng transcript và translation.
- Export TXT tạo file UTF-8 đọc được. Nếu chọn CSV, file phải có cấu trúc CSV hợp lệ; nếu không, mở defect.
- Clear All xóa lịch sử của phiên hiện tại trong UI, không xóa WAV/JSON local và không làm app đóng.

## 11. Trung tâm tài khoản

### TC-ACC-01: Mở Account Center khi đang dịch

1. Nhấn Start và để pipeline ở trạng thái listening.
2. Nhấn biểu tượng Account trên header.
3. Kiểm tra profile, plan, usage và devices.
4. Chờ khoảng 30 giây hoặc nhấn **Làm mới**.
5. Nhấn **Quay lại màn hình dịch**.

**Kết quả mong đợi:**

- Pipeline không bị dừng chỉ vì mở Account Center.
- Translation vẫn được cập nhật nền nếu có audio.
- Usage và thiết bị được làm mới.
- Nút Back chỉ có khi tài khoản active.

### TC-ACC-02: Đặt lại mật khẩu từ Account Center

1. Nhấn **Gửi email đặt lại mật khẩu**.
2. Kiểm tra thông báo trong trang.
3. Kiểm tra email.

**Kết quả mong đợi:**

- App hiển thị thông báo trung tính.
- Firebase gửi email reset password.
- App không yêu cầu nhập hoặc lưu mật khẩu mới trực tiếp.

### TC-ACC-03: Đăng xuất và đăng nhập lại

1. Khi pipeline đang chạy, mở Account Center.
2. Nhấn **Đăng xuất** và xác nhận.
3. Quan sát tiến trình dừng pipeline.
4. Đăng nhập lại cùng tài khoản.

**Kết quả mong đợi:**

- Pipeline dừng an toàn trước khi sign out hoàn tất.
- App không đóng; cửa sổ chính quay về Login.
- UI translation, console và retry queue được xóa khỏi phiên trước.
- Data folder và file local vẫn tồn tại.
- Device identity được giữ; đăng nhập lại không chiếm thêm một device slot.

### TC-ACC-04: Ghi nhớ đăng nhập

1. Đăng nhập thành công và vào Translation.
2. Thoát hoàn toàn app bằng menu tray **Exit**.
3. Mở lại app.

**Kết quả mong đợi:**

- Refresh token được đọc từ Windows Credential Manager.
- Nếu token và subscription còn hợp lệ, app tự vào Translation.
- Không lưu password dạng plaintext.
- Không tạo `auth.json` plaintext trên Windows.

## 12. Quota, lỗi mạng và retry

### TC-ERR-01: Mất mạng khi đang có session

1. Đăng nhập và đảm bảo account active.
2. Ngắt kết nối mạng.
3. Nếu đang ở Translation, phát một đoạn audio hợp lệ.
4. Nếu khởi động lại app khi offline, quan sát trang Offline.
5. Khôi phục mạng.
6. Nhấn **Retry Failed Audio** trong Developer Console nếu nút xuất hiện.

**Kết quả mong đợi:**

- Mất mạng không tự động xóa session.
- App không đóng hoặc mất file WAV local.
- Failed audio được giữ để retry.
- Sau khi có mạng, retry thành công và không tạo bản ghi quota trùng cho cùng request ID.
- Lỗi preview language không tồn tại vì chức năng preview đã bị gỡ.

### TC-ERR-02: Hết quota ngày

1. Ghi lại quota Free hiện tại trên Web Admin và dùng tài khoản Free riêng để dịch đủ quota đó trong ngày UTC.
2. Thử gửi thêm một segment.
3. Mở Account Center và nhấn Refresh.
4. Kiểm tra banner quota và thời gian đếm ngược tới 00:00 UTC.
5. Sau khi sang kỳ UTC mới, nhấn Retry Failed Audio.

**Kết quả mong đợi:**

- App hiển thị `DAILY_QUOTA_EXCEEDED`, dừng pipeline và giữ WAV local.
- Usage cho thấy 0 phút còn lại.
- App không tự đăng xuất và không mất failed audio.
- Sau thời điểm reset, usage ngày mới bắt đầu từ 0 và Retry Failed Audio hoạt động.

## 13. Trạng thái subscription và thiết bị

### TC-STATE-01: Suspend và khôi phục tài khoản

1. Khi app đang active, mở user trên Web Admin.
2. Mở Account Center trên app và nhấn **Refresh** liên tục trong khi Admin thao tác bước tiếp theo.
3. Trên Web Admin, chọn status **Suspended/Tạm khóa** và cập nhật.
4. Tiếp tục refresh app hoặc để auto-refresh chạy ít nhất hai chu kỳ, rồi refresh lại trang user trên Admin.
5. Thử bắt đầu dịch.
6. Trên Web Admin, đổi status về **Active/Hoạt động**.
7. Trên app, nhấn Refresh.

**Kết quả mong đợi:**

- Khi suspended, pipeline dừng và app vào Account Center restricted.
- Trạng thái trên Firestore/Web Admin vẫn là `suspended`; request đồng bộ danh tính từ app không được ghi đè thành `active` hoặc Free.
- App hiển thị đúng thông báo tạm khóa và không có nút Back to Translation.
- Sau khi active lại, app quay về trạng thái có thể dịch.
- Audit log ghi cả hai thay đổi trạng thái.

### TC-STATE-02: Expired

1. Trên Web Admin, đổi status user thành **Expired/Hết hạn**.
2. Refresh app.
3. Sau khi xác nhận restricted, dùng **Kích hoạt hoặc gia hạn** để active lại.

**Kết quả mong đợi:**

- App chặn dịch và hiển thị gói hết hạn.
- User vẫn xem được profile và danh sách thiết bị.
- Gia hạn khôi phục quyền dịch.

### TC-DEV-01: Hai thiết bị hợp lệ và thiết bị thứ ba

1. Đăng nhập user test trên máy thứ nhất.
2. Đăng nhập cùng user trên máy thứ hai.
3. Mở Account Center trên cả hai máy và Refresh.
4. Thử đăng nhập trên máy hoặc Windows profile thứ ba.

**Kết quả mong đợi:**

- Hai thiết bị đầu tiên active.
- Thiết bị thứ ba bị từ chối vì `max_devices=2`.
- Cùng một installation đăng nhập lại không tạo thêm device.

### TC-DEV-02: User revoke thiết bị khác

1. Trên máy thứ nhất, mở Account Center.
2. Xác nhận thiết bị hiện tại có badge **Thiết bị này** và không có nút Revoke.
3. Chọn Revoke cho thiết bị thứ hai và xác nhận.
4. Trên máy thứ hai, thử dịch hoặc Refresh.

**Kết quả mong đợi:**

- User không thể tự revoke thiết bị hiện tại từ UI.
- Thiết bị khác bị revoke thành công.
- Máy bị revoke nhận trạng thái restricted hoặc `DEVICE_REVOKED` và không dịch được.

### TC-DEV-03: Admin revoke và cho phép đăng ký lại

1. Trên Web Admin, mở user test.
2. Nhấn **Thu hồi mọi thiết bị** và xác nhận.
3. Refresh app hoặc gửi một audio request.
4. Trên Web Admin, tìm thiết bị revoked và nhấn **Cho phép đăng ký lại**.
5. Trên app, đăng nhập/Refresh để đăng ký lại thiết bị.

**Kết quả mong đợi:**

- Tất cả device chuyển inactive/revoked.
- App không tự active lại một record đã revoked.
- Sau khi Admin cho phép re-enrollment, app có thể đăng ký lại và hoạt động nếu subscription vẫn active.
- Audit log ghi đúng operator và hành động.

## 14. Kiểm thử Web Admin nâng cao

### TC-ADM-06: Search, filter và pagination

1. Tìm user bằng email đầy đủ.
2. Tìm user bằng UID đầy đủ.
3. Lọc theo từng status.
4. Lọc theo plan `free`.
5. Kết hợp status và plan.
6. Nếu có trên 25 user, kiểm tra Next page và First page.
7. Xóa bộ lọc.

**Kết quả mong đợi:**

- Search email/UID trả đúng user.
- Bộ lọc không làm lộ user ngoài điều kiện.
- Pagination không lặp hoặc bỏ user trong điều kiện dữ liệu ổn định.
- Clear trở về danh sách mặc định.

### TC-ADM-07: Audit log

Thực hiện tối thiểu các thao tác:

1. Lưu plan.
2. Kích hoạt subscription.
3. Suspend user.
4. Active user.
5. Revoke devices.
6. Allow device re-enrollment.
7. Quay lại Dashboard.

**Kết quả mong đợi:**

- Audit log có action tương ứng.
- Operator đúng tài khoản IAP đang đăng nhập.
- Timestamp hợp lý.
- Không ghi password, token hoặc audio/transcript vào audit log UI.

## 15. Nâng cấp ứng dụng Windows

### TC-UPG-01: Nâng cấp khi app đang chạy

1. Đảm bảo app đang chạy và đã có dữ liệu dịch local.
2. Mở installer phiên bản mới.
3. Quan sát cảnh báo ứng dụng đang sử dụng file cần cập nhật.
4. Chọn **Automatically close the applications**.
5. Tại trang vị trí cài đặt, kiểm tra hai đường dẫn.
6. Chọn lại Data folder cũ nếu muốn tiếp tục dùng lịch sử cũ.
7. Hoàn tất nâng cấp và mở app.

**Kết quả mong đợi:**

- Installer đóng app an toàn trước khi thay file.
- Installer không xóa Data folder cũ.
- Mỗi lần chạy installer, đường dẫn trở về mặc định theo install scope; tester phải chọn lại đường dẫn cũ khi cần giữ luồng dữ liệu.
- Nếu chọn đúng Data folder cũ, app tiếp tục thấy dữ liệu local.
- Session đăng nhập được giữ nếu credential còn hợp lệ.

### TC-UPG-02: Chọn Data folder mới khi nâng cấp

1. Chạy lại installer.
2. Chọn một Data folder mới và hợp lệ.
3. Hoàn tất và mở app.

**Kết quả mong đợi:**

- App ghi dữ liệu mới vào Data folder mới.
- Data folder cũ vẫn còn nguyên.
- App không tự sao chép hoặc xóa dữ liệu cũ nếu không có chức năng migration tương ứng.

## 16. Gỡ cài đặt

### TC-UN-01: Uninstall và giữ dữ liệu

1. Đăng xuất khỏi app để loại bỏ refresh token của user test.
2. Thoát app hoàn toàn.
3. Gỡ PRANA ELEX từ Windows Settings hoặc uninstaller.
4. Kiểm tra Application folder.
5. Kiểm tra Data folder.
6. Kiểm tra desktop shortcut và autostart shortcut.

**Kết quả mong đợi:**

- File chương trình và shortcut được gỡ.
- Data folder, WAV và JSON được giữ nguyên.
- Uninstall không gửi request xóa user, subscription hoặc cloud data.
- Device registration phía server vẫn tồn tại cho đến khi user/Admin revoke.

### TC-UN-02: Cài lại và dùng Data folder cũ

1. Cài lại cùng phiên bản hoặc phiên bản mới.
2. Chọn chính xác Data folder cũ.
3. Đăng nhập lại user test.
4. Kiểm tra lại Data folder và mở một WAV/JSON cũ.

**Kết quả mong đợi:**

- App hoạt động bình thường sau reinstall.
- File cũ không bị ghi đè ngoài ý muốn.
- WAV/JSON cũ vẫn đọc được trực tiếp trong Data folder.
- Màn hình History hiện là lịch sử của phiên chạy; không bắt buộc tự nạp lại JSON cũ sau restart hoặc reinstall.

## 17. Security acceptance checklist

Đánh dấu `PASS` cho từng mục:

- [ ] Installer không chứa service-account JSON.
- [ ] Application folder không chứa `.secrets`, PFX, PEM hoặc private key Google Cloud.
- [ ] User không cần tài khoản Google Cloud.
- [ ] User chỉ đăng nhập bằng tài khoản PRANA ELEX/Firebase.
- [ ] Web Admin bắt buộc Google IAP và allowlist.
- [ ] Tài khoản Firebase user không truy cập được Web Admin.
- [ ] Token Windows không được lưu plaintext trong Data folder.
- [ ] Result JSON không chứa token hoặc credential.
- [ ] Sign out không xóa dữ liệu local nhưng xóa phiên user khỏi UI.
- [ ] Revoke thiết bị chặn request audio tiếp theo.
- [ ] Suspended/expired chặn dịch nhưng không phá dữ liệu local.
- [ ] Cloud Run API/Admin vẫn hoạt động khi máy tester không có Google credential.

## 18. Regression checklist giao diện

Kiểm tra ở DPI 100%, 125%, 150% và 200%:

- [ ] Installer EN/VI không tràn chữ.
- [ ] Login/Register không cắt input hoặc nút.
- [ ] Checklist mật khẩu đọc được.
- [ ] Header Translation căn đều locale, Start/Stop, Settings, Account và RX.
- [ ] Language bar có hai cột cân bằng.
- [ ] Stop và RX Active có độ tương phản rõ.
- [ ] Status bar không còn Latency.
- [ ] Settings không tràn tiêu đề section vào card.
- [ ] Account Center không cắt device/action.
- [ ] Web Admin desktop không tràn audit action, email hoặc timestamp.
- [ ] Web Admin tablet/mobile mở và đóng sidebar đúng.
- [ ] Màu status active, pending, suspended và expired phân biệt rõ.

## 19. Mẫu báo cáo lỗi

```text
Defect ID:
Title:
Test case ID:
Environment: Staging
App/Web revision:
Windows/browser:
Account status:
Plan:

Preconditions:

Steps to reproduce:
1.
2.
3.

Actual result:

Expected result:

Reproducibility: x/y
Severity: Blocker / Critical / Major / Minor
Timestamp:
Attachments: screenshot, video, sanitized console log
```

## 20. Điều kiện nghiệm thu test run

Một test run được chấp nhận khi:

- Tất cả luồng cài mới, đăng ký, xác minh, kích hoạt, dịch và gỡ cài đặt đều `PASS`.
- Không còn lỗi Blocker hoặc Critical.
- Lỗi Major có đánh giá ảnh hưởng và quyết định release rõ ràng.
- Security acceptance checklist đạt toàn bộ.
- Không phát hiện credential trong package hoặc dữ liệu output.
- Quota, suspend, expired và device revoke đều chặn dịch đúng.
- Retry mạng không làm mất audio local hoặc tính quota trùng.
- Web Admin audit ghi đúng operator cho thao tác quan trọng.

## Phụ lục A: Kiểm thử Raspberry Pi 4B

Áp dụng cho Raspberry Pi OS Desktop Bookworm 64-bit.

### PI-01: Cài package

1. Sao chép `prana-elex_1.1.0_arm64.deb` vào Pi.
2. Chạy:

   ```bash
   sudo apt install ./prana-elex_1.1.0_arm64.deb
   ```

3. Mở PRANA ELEX từ menu hoặc chạy `prana-elex`.

**Kết quả mong đợi:**

- Package cài vào `/opt/prana-elex`.
- Launcher tồn tại tại `/usr/bin/prana-elex`.
- Menu entry xuất hiện.
- App chạy native ARM64.

### PI-02: Data Setup và đăng nhập

1. Ở lần chạy đầu, chọn Data folder trong trang Data Setup của app.
2. Đăng nhập user staging đã active.
3. Chọn audio device phù hợp.
4. Thực hiện một bản dịch.

**Kết quả mong đợi:**

- Linux/Pi được phép chọn Data folder trong app nếu chưa có settings.
- Settings nằm tại `~/.config/prana-elex/settings.json`.
- Token ưu tiên Secret Service; fallback `auth.json` phải có mode `0600`.
- Data mặc định là `~/PRANA_ELEX_Data` nếu không có lựa chọn khác.

### PI-03: Gỡ package

1. Chạy:

   ```bash
   sudo apt remove prana-elex
   ```

2. Kiểm tra settings, token fallback và Data folder.

**Kết quả mong đợi:**

- File ứng dụng bị gỡ.
- Settings, credential user và dữ liệu local được giữ.
- Không xóa tài khoản Firebase hoặc device server.

## Phụ lục B: Quick smoke test sau mỗi deploy

1. Mở `PRANA API /health` và xác nhận trả `{"status":"ok"}`.
2. Xác nhận revision API/Admin đúng với test run trước khi tiếp tục.
3. Mở Web Admin bằng tài khoản IAP hợp lệ.
4. Kiểm tra Dashboard, Users và Plans trả trang bình thường.
5. Đăng nhập app bằng Email/Password và Google trên hai lượt độc lập.
6. Refresh Account Center.
7. Mở Plans, giữ trang trong ít nhất 30 giây và xác nhận catalog không biến mất hoặc quay về giá trị cũ.
8. Chạy một đoạn audio 10 giây.
9. Xác nhận transcript, translation và API OK.
10. Kiểm tra usage tăng trên app và Web Admin.
11. Sign out rồi sign in lại.
12. Xác nhận không tạo thêm device.

Nếu một trong mười hai bước thất bại, dừng phát hành và mở defect trước khi build installer production.

## Phụ lục C: Regression kỹ thuật bắt buộc trước khi phát hành

Các kiểm tra dưới đây dành cho QA Lead hoặc Backend tester; không dùng công cụ tạo tải
trực tiếp lên staging nếu chưa được người quản lý môi trường chấp thuận.

### REG-API-01: Transaction đồng bộ danh tính

1. Chạy:

   ```powershell
   .venv\backend\Scripts\python.exe -m unittest tests.api.test_subscription_plans -v
   ```

2. Xác nhận test profile không đổi không phát sinh update và tài khoản suspended không nhận lại Free.
3. Thực hiện lại `TC-STATE-01` trên staging để kiểm tra hành vi đồng thời thực tế.

**Kết quả mong đợi:** toàn bộ test đạt; trạng thái Suspend luôn thắng khi Admin và app cập nhật đồng thời.

### REG-API-02: OAuth rate-limit không phụ thuộc IP

1. Chạy:

   ```powershell
   .venv\backend\Scripts\python.exe -m unittest tests.api.test_google_auth -v
   ```

2. Xác nhận các test sau đạt:
   - Queue cục bộ có kích thước hữu hạn và chặn sau giới hạn instance.
   - Hai instance giả lập dùng chung bộ đếm Firestore.
   - Request vượt giới hạn toàn cục bị chặn trước Google token exchange.
   - Cửa sổ mới reset bộ đếm.
   - Firestore lỗi trả `503 GOOGLE_AUTH_UNAVAILABLE`.
3. Trên staging, thực hiện một lượt đăng nhập Google bình thường để xác nhận limiter không chặn traffic hợp lệ.

**Kết quả mong đợi:** không dùng `X-Forwarded-For` làm khóa; lỗi giới hạn trả `429 RATE_LIMITED` và `Retry-After`; lỗi Firestore fail closed.

### REG-API-03: Plans polling không ghi user document

1. Ghi lại `updated_at` của user test trong Firestore hoặc công cụ quan sát được cấp quyền.
2. Mở trang Plans trong app và để polling chạy ít nhất ba chu kỳ, tối thiểu 90 giây.
3. Không đăng nhập lại, không chọn plan và không quay về Account Center trong thời gian này.
4. Đọc lại `updated_at` của user.
5. Quay về Account Center và xác nhận profile/usage được tải mới.

**Kết quả mong đợi:** catalog Plans vẫn cập nhật nhưng `updated_at` của user không thay đổi; Account Center vẫn nhận profile và usage mới khi mở lại.
