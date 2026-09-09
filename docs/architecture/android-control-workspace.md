# Android: Control và cấu hình theo module

## Thay đổi ngày 2026-09-09

Workspace có ba tab **Dashboard | Control | Live VHF**. Route mới
`/stations/:id/control` dùng cùng workspace key theo user/Station. Settings mở
từ header, quay về tab nguồn; History vẫn thuộc Live VHF.

- Dashboard chỉ hiển thị Speed, Depth, Heading và trạng thái telemetry.
- Control giữ tọa độ cố định dưới tab bar. Map, freshness/thời gian mẫu,
  Auto/Manual và vô lăng nằm trong vùng cuộn. Màn rộng chia 2:1; màn hẹp xếp dọc.
- Settings có VHF Device, Speed Device, Device 3 và Device 4. VHF giữ nguyên
  capture mode, RX input, TX output và cơ chế đồng bộ. Ba mục còn lại chỉ báo
  **Chưa tích hợp**, không chọn thiết bị, không lưu, không gọi phần cứng.
  Đây là vai trò module, không phải số cổng USB.

## Ownership và ranh giới

```text
app/di/telemetry_providers.dart
  -> station/shared/application/StationTelemetryController
     -> TelemetryRepository (một subscription)
     -> Dashboard + Control + StationRuntimeState projection

ControlTab (key user/Station, được giữ khi đổi tab)
  -> SteeringState (chỉ UI, không repository)
  -> SteeringWheel CustomPainter + gestures + semantics
```

Controller/state telemetry trước đây thuộc Dashboard được chuyển sang Station
shared và đổi tên. Map/Position/Control widget chuyển sang feature Control;
Status widget chuyển sang shared. Không giữ re-export bridge.

Mode và góc lái nằm trong ControlTab, không thuộc telemetry. Manual kéo xoay
liên tục qua điểm nối góc; giới hạn −180°…+180°, thả giữ góc, trái/phải bước 5°,
Về giữa trả về 0°. Auto đưa về 0° và khóa điều chỉnh. Chuyển tab kết thúc gesture
nhưng giữ góc/mode; đóng workspace hoặc đổi user/Station tạo lại state.

Vô lăng không sửa heading/tọa độ của mock, không gửi lệnh Station. Painter cập
nhật trực tiếp, không có animation tự chạy; hỗ trợ semantics tăng/giảm và các
nút tối thiểu 48dp. REST, Firestore, TX/RX runtime, Python, Web Admin và Desktop
không thay đổi trong iteration này.

## Bằng chứng kiểm chứng

- Toàn bộ Flutter tests: **157 PASS** (`build/buildapp/control-tests-final.log`).
- Sau chỉnh bố cục nút và retry: Control unit/widget/matrix **3 PASS**
  (`build/buildapp/control-wheel-final.log`).
- Analyze không có issue; format được kiểm tra bằng lệnh không ghi file.
- Matrix: 320/375/390/400/430/768/1024/1440/1920, Việt/Anh, chữ 1/1.5/2;
  thêm landscape thấp trong workspace. Tọa độ giữ vị trí sau khi cuộn.
- Regression: ba tab/deep link, Settings Back về Control, góc giữ qua Settings,
  một subscription, runtime/recorder không tạo lại, không START/STOP; các test
  draft, TX, History và user lifecycle hiện có tiếp tục PASS.
- Emulator API 36: attach/hot restart bản staging debug đã cài để xem UI,
  không build APK mới. Ảnh cục bộ trong `build/buildapp/control-*.png`.

**CHƯA KIỂM CHỨNG phần cứng:** Station quan sát trên emulator có trạng thái
Online/Idle, nhưng không chủ động START/STOP, thu/phát RF hoặc điều khiển PTT.
Speed Device và hai module dự phòng chưa có tích hợp thật. Vô lăng và telemetry
tiếp tục là mô phỏng.
