# PRANA ELEX Mobile

Ứng dụng Flutter Android dùng để ghép nối, điều khiển và theo dõi các station
PRANA ELEX. Ứng dụng không kết nối trực tiếp với laptop hoặc Raspberry Pi. Các
thao tác thay đổi trạng thái được gửi qua REST API, còn trạng thái và kết quả
theo thời gian thực được nhận từ Firestore snapshot.

## Yêu cầu môi trường

- Flutter stable với phiên bản Dart SDK tương thích với `pubspec.yaml`.
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
.\run_mobile.bat
```

Lệnh này tự động:

1. Kiểm tra Flutter, Android SDK và file cấu hình staging.
2. Sử dụng emulator đang online hoặc mở `Prana_API_36` bằng cold boot.
3. Đợi Android boot hoàn tất.
4. Chạy ứng dụng Flutter Staging trên emulator.

Trong terminal đang chạy Flutter, nhấn `r` để Hot Reload, `R` để Hot Restart và
`q` để dừng ứng dụng. Emulator vẫn được giữ lại sau khi dừng app.

Trong VS Code, có thể dùng `Ctrl+Shift+B` rồi chọn **PRANA: Mở Android App**. Task
này đã được đặt làm build task mặc định nên các lần sau chỉ cần nhấn
`Ctrl+Shift+B`.

Muốn chạy production:

```powershell
.\run_mobile.bat -Flavor production
```

## Mở mô phỏng thủ công

1. Mở Android Studio và chọn **Device Manager**.
2. Nhấn nút chạy bên cạnh `Prana_API_36` và đợi màn hình Android xuất hiện.
3. Mở thư mục gốc dự án trong VS Code.
4. Chọn `emulator-5554` bằng lệnh **Flutter: Select Device**.
5. Mở **Run and Debug**, chọn **PRANA Mobile - Staging** rồi nhấn `F5`.

Hoặc chạy trực tiếp trong thư mục `apps/prana_mobile`:

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
prana-station-provision --config config/profiles/raspberry-pi.toml --output ~/prana-station-label
```

Lệnh giữ nguyên Ed25519 identity của station, đăng ký activation hash với backend
và tạo tem PNG/SVG. Tem gồm QR, Setup ID và Activation Code để nhập tay dự phòng.
Không chia sẻ ảnh tem trước khi bàn giao thiết bị.

Sau khi in tem, chạy station bình thường:

```bash
prana-station --config config/profiles/raspberry-pi.toml
```

Station chưa được claim sẽ chờ người dùng quét tem. Các station cũ chưa provision
vẫn tiếp tục tạo mã ghép tạm thời có hiệu lực 10 phút.

## Kiểm tra

```powershell
flutter analyze
flutter test
flutter test --device-id <emulator-id>
```
