# PRANA ELEX — Web UI Preview

Chạy từ repo root trên Windows với Flutter SDK đã cài:

```powershell
.\run\_android\_preview.bat
```

Địa chỉ: http://127.0.0.1:8876. Lần đầu Flutter có thể tải Web SDK; những lần
sau dùng cache. Giữ terminal mở: `r` hot reload, `R` hot restart, `q` thoát.
Đổi cấu trúc bootstrap/provider có thể cần `R`. Không build APK, không deploy.

Launcher mặc định ưu tiên Chrome (hỗ trợ `CHROME_EXECUTABLE`). Khi không có
Chrome, nó dùng `web-server` và mở trình duyệt mặc định khi server sẵn sàng.
Có thể chọn trực tiếp:

```powershell
.\run\_android\_preview.bat -Browser chrome
.\run\_android\_preview.bat -Browser edge
.\run\_android\_preview.bat -Browser web-server
```

Nếu Chrome/Edge không nhận kết nối debug, dùng `-Browser web-server`; hot reload
vẫn hoạt động, nhưng debugging nâng cao cần Dart Debug extension. Cổng 8876
đang bận sẽ báo lỗi, không dừng server khác. Server chỉ bind loopback.

## Màn hình và thao tác

- Hai Station: VINH online/idle và Harbor offline. Dashboard đã được gộp vào
  Control trong source hiện tại; preview giữ nguyên Control và Live VHF,
  gồm instrument, bản đồ, tọa độ và vô lăng. Link `/dashboard` vẫn về Control.
- START/STOP chỉ đổi trạng thái demo. Khi running, mỗi 5 giây có một RX mới;
  Live và History dùng chung dữ liệu. History RX/TX có mẫu hôm nay và hai ngày trước.
- HTT: bật START rồi giữ nút thu, nhả để tạo draft. Confirm mô phỏng queued,
  transmitting và completed trong khoảng 6 giây. Không xin mic, không phát âm thanh.
- History có tìm kiếm, ngày, RX/TX và detail. Playback mô phỏng 2 giây và dừng
  khi rời trang hoặc background; tách biệt với Auto Audio.
- Settings dùng thiết bị USB demo. Country và plan cập nhật trong phiên.
  Ghép Station, liên kết Google và gửi email không thực hiện dịch vụ thật.
- Account & Plan đổi EN/VI và dark mode như App. Chỉ hai lựa chọn thị giác này
  lưu ở browser localStorage, namespace `prana.ui-preview.*`; khi browser chặn
  storage thì chỉ lưu trong bộ nhớ. Không đọc storage/credentials của mobile.
- Thanh công cụ riêng có nhãn mô phỏng, nút cỡ chữ 1×/1.5×/2× và reset demo.
  Reset tạo lại toàn bộ session, giữ locale/theme. Sign out hiện màn kết thúc;
  vào lại tạo phiên mới. Reload browser cũng tạo phiên demo mới.

## Kiến trúc

`main_preview.dart` → `preview/preview_app.dart` → `PranaMobileApp` và router thật.
Mobile `main.dart` không thay đổi và không import preview.

| Thành phần | Trách nhiệm |
| --- | --- |
| `preview/demo_store.dart` | Kho phiên dùng chung: Station/projection, RX/History, TX, Settings, account; clock có thể inject |
| `preview/demo_api.dart` | Implements `PranaApi` mà không gọi constructor Dio/Firebase; thao tác không hỗ trợ fail closed |
| `preview/demo_adapters.dart` | Auth demo, StationRepository, recorder, TxRepository, speech/source/history playback giả |
| `preview/preview_storage.dart` | Giữ contract secure storage cho controller hiện có; conditional import localStorage Web/memory test |
| `preview/preview_app.dart` | Provider overrides, toolbar, session reset; chặn Firebase/Firestore trực tiếp |
| `domain/radio/history_audio_engine.dart` | Interface phát History được inject |
| `data/radio/history_audio.dart` | Adapter native giữ download, file tạm, audio và cleanup ngoài widget |

Preview dùng stream từ kho demo thay cho live polling HTTP; telemetry giữ mock
repository/controller hiện có. Chuyển tab giữ cùng runtime, recorder và subscription.
History Screen sở hữu một player; rời tab/đóng widget hủy playback. Account dùng
AuthenticationService cho link Google, reset password và resend verification.
Router chỉ thêm điểm inject cho màn sign-in/pairing, không nhân bản bảng route.
Mọi implementation native vẫn biên dịch trong dependency graph; preview không
khởi tạo chúng. Web JavaScript compile đã xác nhận không cần thêm package.

## Kiểm chứng

Từ `apps/android`:

```powershell
flutter gen-l10n
dart format --output=none --set-exit-if-changed lib test
flutter analyze --no-pub
flutter test --no-pub
flutter build web --target lib/main_preview.dart --no-pub --no-web-resources-cdn
```

`preview_test.dart` kiểm tra shared store, Settings/Country/plan, persistence,
route/runtime/telemetry identity, HTT qua tab, TX, sign out/reset, late Future
và cleanup. Firebase/Firestore bị chặn; API là adapter không tạo Dio.
`preview_layout_test.dart` render sáu màn qua widths 320/375/390/400/430/768/1024/1920
và 800×360; EN/VI, sáng/tối, chữ 1×/1.5×/2×. Kiểm tra exception layout và text clipping.

Các kết quả này là **mock/contract/UI evidence**. Preview không chứng minh audio,
camera, lifecycle native, RF/PTT hoặc phần cứng. Không có APK/iOS build trong iteration.
Flutter Web JavaScript chạy được; Wasm chưa là mục tiêu (plugin `flutter_tts`
hiện phát cảnh báo Wasm dry-run). Không đổi dependency để xử lý cảnh báo này.

### Kết quả iteration 12/09/2026

- Baseline: 185 Flutter tests. Sau thay đổi: **201/201 PASS**;
  lần kiểm tra cuối chạy tuần tự với `--concurrency 1`.
- Localization generation, format (143 files, 0 thay đổi), analyze: **PASS**.
- Android packaging/runner regression: **17/17 PASS** (4 cảnh báo Pillow có sẵn).
- Web JavaScript compile: **PASS**. Còn cảnh báo Wasm của `flutter_tts` và font
  Cupertino trong dependency graph; không có lỗi compile.
- Mock widget matrix: **648 tổ hợp màn hình/layout PASS** (6 màn × 9 viewport ×
  2 locale × 2 theme × 3 text scale). Có sửa nhãn thiết bị Settings để xuống dòng
  và trạng thái Station list để không tràn ở 320 px/chữ lớn.
- Browser localhost: đã mở Station/Control/Live/History/Account; START sinh RX,
  HTT tạo review, confirm tạo bản History TX Completed; đổi EN/VI, bật dark mode,
  chọn/lưu USB demo trong Settings. Đã xem render portrait 320/375/390/430/768 px,
  tablet 1024×768, desktop 1920×800 và landscape 800×360, gồm chữ 2×/dark mode.
  Ma trận đầy đủ nêu trên là widget evidence,
  không phải tuyên bố đã xem thủ công mọi tổ hợp trong browser.
- Launcher báo rõ khi cổng bận. Hot reload đã thực hiện khoảng 0,55 giây.
  Máy kiểm chứng không có Chrome; Edge debug launch thất bại, Web Server chạy được.
- Test TX có sẵn dùng timer thực 5 ms từng fail khi tranh CPU với Web compile;
  dùng `flutter test --no-pub --concurrency 1` khi cần tránh cạnh tranh tài nguyên.
- Audio/camera/native lifecycle/RF/PTT/phần cứng: **CHƯA KIỂM CHỨNG** bằng preview.
