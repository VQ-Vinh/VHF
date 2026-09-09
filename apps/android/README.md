# PRANA ELEX Mobile

Ứng dụng Flutter Android dùng để ghép nối, điều khiển và theo dõi các station
PRANA ELEX. Ứng dụng không kết nối trực tiếp với laptop hoặc Raspberry Pi; mọi
thao tác, trạng thái và kết quả đều đi qua Public API.

Người dùng thông thường cài APK từ
[GitHub Releases](https://github.com/VQ-Vinh/VHF/releases) và không cần cài
Flutter, Android SDK hoặc Emulator. Phần còn lại của tài liệu này dành cho lập
trình viên Android.

## Yêu cầu môi trường

- Flutter stable 3.44.8 trở lên với phiên bản Dart SDK tương thích với
  `pubspec.yaml`. Built-in Kotlin sẽ được bật khi Flutter stable 3.47+ phát
  hành; Flutter 3.44.x vẫn dùng lớp tương thích KGP.
- Android Studio, Android SDK 26 trở lên và điện thoại hoặc Android Emulator.
- JDK 17 trở lên; có thể dùng JDK đi kèm Android Studio.
- Firebase đã bật phương thức đăng nhập Email/Password và Google.

Android Gradle wrapper đã được lưu trong thư mục dự án. Không chạy `flutter
create` đè lên ứng dụng vì lệnh này có thể thay thế cấu hình flavor và manifest
hiện tại.

## Cấu hình

Sao chép `config/staging.example.json` thành `config/staging.json`, sau đó điền
các thông số public của ứng dụng Firebase Android. Các file cấu hình thật đã
được Git bỏ qua. Firebase API key chỉ dùng để xác định Firebase project; tuyệt
đối không đặt service-account key hoặc OAuth client secret trong thư mục này.

Trên Android Emulator, địa chỉ `10.0.2.2` trỏ đến API development đang chạy trên
máy tính host.

## Mở mô phỏng nhanh

Từ thư mục gốc của dự án, chạy một lệnh:

```powershell
.\run_android_emulator.bat
```

Lệnh này tự động:

1. Kiểm tra Flutter, Android SDK và file cấu hình staging.
2. Sử dụng emulator đang online hoặc mở `Prana_API_36` bằng cold boot.
3. Đợi Android boot hoàn tất.
4. Chạy ứng dụng Flutter Staging trên emulator.

Emulator `Prana_API_36` mặc định chạy ở `1080x2160` (18:9). Muốn thử
một tỷ lệ khác:

```powershell
.\run_android_emulator.bat -EmulatorResolution 1080x1920
```

Trong terminal đang chạy Flutter, nhấn `r` để Hot Reload, `R` để Hot Restart và
`q` để dừng ứng dụng. Emulator vẫn được giữ lại sau khi dừng app.

## Build APK nhanh

Từ thư mục gốc, build APK staging debug bằng một lệnh:

```powershell
.\build_android_apk.bat
```

Các lựa chọn khác:

```powershell
# Staging release
.\apps\android\build.bat -Flavor staging -BuildMode release -PhysicalDevice

# Production release; yêu cầu keystore production
.\apps\android\build.bat -Flavor production -PhysicalDevice

# Xóa build cache trước khi build
.\apps\android\build.bat -PhysicalDevice -Clean
```

`BuildMode=auto` là mặc định: staging dùng debug, production dùng release. APK được
tạo trong `build/buildapp/flutter/app/outputs/flutter-apk/` và copy vào
`installers/android/<flavor>/`. Script không chứa hoặc
sao chép Firebase credential, keystore hay signing password.

Trong VS Code, có thể dùng `Ctrl+Shift+B` rồi chọn **PRANA: Mở Android App**. Task
này đã được đặt làm build task mặc định nên các lần sau chỉ cần nhấn
`Ctrl+Shift+B`.

Muốn chạy production:

```powershell
.\run_android_emulator.bat -Flavor production
```

## Mở mô phỏng thủ công

1. Mở Android Studio và chọn **Device Manager**.
2. Nhấn nút chạy bên cạnh `Prana_API_36` và đợi màn hình Android xuất hiện.
3. Mở thư mục gốc dự án trong VS Code.
4. Chọn `emulator-5554` bằng lệnh **Flutter: Select Device**.
5. Mở **Run and Debug**, chọn **PRANA Mobile - Staging** rồi nhấn `F5`.

Hoặc chạy trực tiếp trong thư mục `apps/android`:

```powershell
flutter pub get
flutter run --flavor staging --dart-define-from-file=config/staging.json
```

Môi trường production sử dụng file `production.json` và flavor `production`
tương ứng. Các launch profile dành cho VS Code nằm trong `.vscode/launch.json`.

### Ký bản production

Không dùng debug key cho bản phát hành. Cấu hình keystore bằng các biến môi trường:

```powershell
$env:PRANA_ANDROID_KEYSTORE_PATH="D:\secure\prana-upload.jks"
$env:PRANA_ANDROID_KEYSTORE_PASSWORD="..."
$env:PRANA_ANDROID_KEY_ALIAS="prana-upload"
$env:PRANA_ANDROID_KEY_PASSWORD="..."
flutter build appbundle --release --flavor production --dart-define-from-file=config/production.json
```

Hoặc đặt bốn giá trị tương ứng `storeFile`, `storePassword`, `keyAlias`, `keyPassword`
trong `android/key.properties`. File này đã được Git bỏ qua. Build production release sẽ
dừng với thông báo rõ ràng nếu chưa cấu hình đủ credential.

## Thiết lập Firebase

Bật đăng nhập Email/Password và Google, sau đó đăng ký application ID cho cả
staging và production, bao gồm suffix của staging. Đăng ký SHA fingerprint cho
cả bản development và release. Triển khai
`infra/firebase/firestore.rules` trước khi sử dụng Firestore listener theo thời
gian thực.

Ứng dụng chỉ được đọc dữ liệu station thuộc tài khoản hiện tại và không được ghi
trực tiếp vào Firestore.

## Provision và in tem Raspberry Pi

Sau khi cài PRANA ELEX trên Pi và cấu hình `backend.api_url`, chạy:

```bash
prana-station-provision --config apps/linux/config/default.toml --output ~/prana-station-label
```

Lệnh giữ nguyên Ed25519 identity của station, đăng ký activation hash với backend
và tạo tem PNG/SVG. Tem gồm QR, Setup ID và Activation Code để nhập tay dự phòng.
Không chia sẻ ảnh tem trước khi bàn giao thiết bị.

Sau khi in tem, chạy station bình thường:

```bash
prana-station --config apps/linux/config/default.toml
```

Station chưa được claim sẽ chờ người dùng quét tem. Các station cũ chưa provision
vẫn tiếp tục tạo mã ghép tạm thời có hiệu lực 10 phút.

## Kiểm tra

```powershell
flutter analyze
flutter test
flutter test --device-id <emulator-id>
```

## Station Workspace

Station list opens Dashboard. Dashboard / Control / Live VHF are the three primary tabs; History and Settings are secondary pages in the retained workspace. Only Live sends START/STOP. Phone TX and Auto Audio belong to the app session, so changing tabs does not restart remote RX or dispose TX. Dashboard and Control share one telemetry subscription. Control contains the simulated map, pinned coordinates and a manual steering wheel with no hardware effect. Settings groups VHF Device and three not-yet-integrated module slots. See [Control architecture and verification](../../docs/architecture/android-control-workspace.md).

See [Android architecture, per-file migration and verification](../../docs/architecture/android-workspace-migration.md).

## Ngôn ngữ giao diện

Nội dung dịch nằm trong `lib/l10n/app_en.arb` (template) và `app_vi.arb`.
Chạy `flutter gen-l10n` sau khi sửa ARB; không sửa trực tiếp các file Dart
`app_localizations*.dart` được sinh. Commit ARB, cấu hình và mã được sinh cùng nhau.
UI gọi getter/hàm có kiểu của `AppLocalizations`, không tra key chuỗi.
Thông báo mã lỗi từ API/Station được chuyển sang getter tại `core/service_messages.dart`;
không thêm nội dung dịch trực tiếp vào adapter này.

Thêm ngôn ngữ bằng một ARB `app_<locale>.arb` có đủ message/placeholder của template,
sinh lại mã, rồi bổ sung Country tương ứng trong `CountryLocalePolicy`.
Mỗi ngôn ngữ vẫn cần bản dịch riêng; ARB tách công việc dịch khỏi code Dart,
và code generation phát hiện lỗi tên message/placeholder.

Account cung cấp EN trước, sau đó ngôn ngữ Country nếu đã hỗ trợ (hiện VN → VI).
Country khác chỉ có EN; trước khi Country được tải và tại đăng nhập, mọi locale
đóng gói đều có thể chọn. Đổi Country giữ locale hợp lệ, nếu không thì chọn ngôn ngữ
Country hoặc EN. Chỉ lưu locale trên điện thoại; không đổi API hay ngôn ngữ RX/TX.
Bộ chọn căn phải, reflow khi không đủ chỗ, giữ vùng bấm tối thiểu 48 logical pixels.

Account & Plan có công tắc Chế độ tối/Dark mode. Lựa chọn được lưu cục bộ,
áp dụng ngay trên toàn ứng dụng và không phụ thuộc theme hệ thống. Theme tối dùng
`ColorScheme` cho surface, chữ, icon, input, map và các điều khiển mô phỏng; khi
thêm UI mới, tránh dùng trực tiếp màu nền hoặc màu chữ chỉ phù hợp theme sáng.

Kiểm tra: `flutter gen-l10n`, `dart format --output=none --set-exit-if-changed lib test`,
`flutter analyze --no-pub`, `flutter test --no-pub`. Test localization kiểm tra ARB,
Country thành công/thất bại, các Future hoàn thành muộn và layout EN/VI ở text scale
1.0/1.5/2.0. Không cần build APK cho thay đổi nội dung dịch thông thường.
