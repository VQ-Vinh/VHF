# Fleet Operator Console (Windows Desktop)

Desktop app (`apps/windows/`) không còn là client dịch thuật cục bộ. Nó là
**console vận hành đội Station**: một tài khoản có quyền `fleet_operator` nhìn
thấy mọi Station trong hệ thống, gắn vào một Station bất kỳ, chiếm quyền điều
khiển, xem Live VHF và phát sóng TX.

Pipeline WASAPI cục bộ đã được gỡ khỏi UI. Nó vẫn sống trong Windows Station
headless (`prana_windows.station`) và `cli.py`; console chỉ dùng micro cho TX.

## Console khác Web Admin ở đâu

Hai công cụ, hai mô hình đe doạ. Đừng để cái này mọc thành cái kia.

| | Web Admin (`services/prana_admin`) | Console (`apps/windows`) |
|---|---|---|
| Danh tính | IAP + allowlist email, không phải Firebase user | Firebase user có cờ `fleet_operator` |
| Truy cập dữ liệu | Firestore trực tiếp bằng service account | REST qua `prana_api`, không bao giờ đụng Firestore |
| Nội dung (transcript/audio) | **Không có, cố ý** | Toàn bộ |
| Điều khiển | Chỉ một nút Stop | Start/Stop, ngôn ngữ, thiết bị, TX |
| Sở hữu | Chuyển/giải phóng Station, quản lý user và gói cước | Không |

## Quyền `fleet_operator`

Cờ boolean trên document `users/{uid}`, **không phải** Firebase custom claim.

Lý do: `verified_account()` (`services/prana_api/main.py`) đã nạp document này
trên **mọi** request đã xác thực, nên đọc cờ không tốn thêm truy vấn nào, và —
quan trọng hơn — **thu hồi có hiệu lực ngay lập tức**. Custom claim nằm trong ID
token nên cả server lẫn client sẽ còn thấy giá trị cũ tới một tiếng sau khi thu
hồi. Với một quyền cho phép đọc liên lạc vô tuyến của mọi khách hàng và chiếm
quyền điều khiển bộ đàm của họ, độ trễ thu hồi là vấn đề an toàn.

Cấp/thu hồi: Web Admin, trang chi tiết user. Đi qua đúng khuôn CSRF +
`admin_audit` như các thao tác quản trị khác.

## Ranh giới API

Router riêng `/v1/operator/*` (`services/prana_api/main.py`), với
`Depends(require_fleet_operator)` ở **cấp router**.

Không thêm nhánh `or is_operator` vào các handler owner. Bất biến *"mọi route
`/v1/stations/*` trả 404 nếu bạn không phải chủ Station"* phải còn chứng minh
được bằng cách đọc từng handler; nếu rải điều kiện vào đó, mỗi lần sửa sau này
biến thành một cuộc rà soát bảo mật. Contract của Android cũng giữ nguyên từng
byte.

### Cách tầng operator tái dùng repository

Tham số `uid` trong mọi hàm repository của Station mang nghĩa **chủ dữ liệu**,
không phải người gọi; việc kiểm tra quyền là một dòng riêng biệt bên trong. Nên
route operator chỉ phân giải `owner_uid` từ `station_registry` rồi gọi **chính
các hàm cũ** với uid đó.

> **Không được nới lỏng bộ lọc tiền tố `users/{uid}/...`.** `release_station`
> xoá `owner_uid`, và Station có thể được người khác claim lại. Bộ lọc đó chính
> là thứ ngăn transcript của chủ cũ lọt sang chủ mới.

### Hạn mức tính theo chủ Station

Cửa sổ history và giới hạn nội dung lấy từ gói cước của **chủ Station**, không
phải của operator. Operator không bao giờ được xem xa hơn những gì khách đã trả
tiền để lưu — đó là cam kết với khách, không phải đặc quyền hỗ trợ.
`HISTORY_LOCKED` giữ nguyên mã và ý nghĩa.

### Audit

Collection riêng `operator_audit` (không dùng chung `admin_audit`, vốn có schema
khoá theo email IAP và được `prana_admin` phân trang). Ghi khi mọi thao tác ghi
**và mọi lần đọc nội dung kết quả**.

## Control lease

Trường `control_lease` trên `station_registry/{station_id}`, mirror sang
`users/{owner_uid}/stations/{station_id}` trong **cùng transaction** — Firestore
rules chỉ cho client đọc projection đó, nên bản mirror là đường duy nhất để điện
thoại của chủ biết mình vừa bị chiếm quyền.

```
control_lease: {
  holder_uid, holder_kind: "owner"|"operator", holder_label,
  acquired_at, expires_at, epoch, preempted_from_uid, preempted_at
}
```

- **TTL 120 s, renew mỗi 45 s** — chịu được hai lần lỡ nhịp.
- **Vắng mặt hoặc hết hạn ⇒ chủ Station ngầm định giữ quyền.** Đây là thứ khiến
  mọi bản Android và mọi Station đang chạy hoạt động bình thường mà không cần
  migration.
- **`epoch` là fencing token**, đơn điệu tăng qua mọi lần chiếm quyền. Người giữ
  phải xuất trình đúng epoch được cấp; thiếu nó, một console ngủ qua một lần bị
  cưỡng chế sẽ hồn nhiên giành lại quyền khi thức dậy.
- Hết hạn được đánh giá **lười**, ngay trong transaction. Không có scheduler.

| Mã lỗi | Nghĩa |
|---|---|
| `CONTROL_HELD` | Người khác đang giữ; gửi lại với `force: true` để cưỡng chế |
| `CONTROL_LOST` | Lease của bạn đã hết hạn hoặc bị chiếm (sai epoch) |
| `CONTROL_TAKEN` | Bạn là chủ Station nhưng một operator đang giữ quyền |

### Cờ triển khai

`PRANA_API_CONTROL_LEASE_ENABLED` (mặc định **false**).

Khi tắt: operator vẫn phải giữ lease để ra lệnh (hai operator không giành nhau),
nhưng **chủ Station không bị hạ quyền** — `CONTROL_TAKEN` không bao giờ phát ra.

> **Chỉ bật cờ này sau khi bản Android có xử lý view-only đã phát hành tới máy
> người dùng.** Một bản Android cũ gặp `CONTROL_TAKEN` sẽ chỉ hiện một lỗi mờ
> đục không được dịch, cho người đang đứng trước một thiết bị liên quan an toàn.

## Client: tại sao là polling

`infra/firebase/firestore.rules` cho user đăng nhập đọc `users/{uid}/stations/*`
và **cấm đọc `results/*` với mọi client**. Hệ quả: operator không thể subscribe
Station mình không sở hữu, và không ai subscribe được kết quả. Console vì vậy
**chỉ dùng REST**, không bao giờ đụng Firestore trực tiếp.

| Poll | Nhịp | Dừng khi |
|---|---|---|
| Danh sách fleet | 10 s | không phải trang đang hiện |
| Chi tiết Station | 2 s | đã tháo / trang bị ẩn / cửa sổ thu nhỏ |
| Live results | 2 s | đã tháo / trang bị ẩn / cửa sổ thu nhỏ |
| Renew lease | 45 s | **không bao giờ, khi còn gắn** |

Renew phải sống sót qua minimize-to-tray: mất quyền âm thầm trong lúc operator
đang xem việc khác tệ hơn hẳn việc nhả quyền tường minh.

## Ngưỡng online

`STATION_ONLINE_SECONDS = 15` (`prana_core/console/models.py`), khớp Android và
Web Admin. Các cổng TX trong `services/prana_api/main.py` **cố ý giữ 20 s**;
siết lại sẽ đổi hành vi của người dùng TX hiện tại mà console chẳng được lợi gì.

## Tìm kiếm fleet

Firestore không có substring search. `GET /v1/operator/stations?query=` khớp:
mã Station **chính xác**, email chủ sở hữu **chính xác**, hoặc **tiền tố** tên.
Không lọc-một-trang-rồi-gọi-là-search — cách đó âm thầm bỏ sót kết quả ở trang
sau. Giới hạn này được nêu ngay trong UI.

## TX của operator

Đây là hành động hệ quả cao nhất trong toàn hệ thống: nó kích máy phát VHF thật
của khách hàng.

Các route `/v1/operator/stations/{id}/tx/*` gọi lại **chính handler của chủ**,
chỉ thêm ba thứ:

1. bắt buộc đang giữ control lease,
2. ghi `operator_audit` **trước** khi kích sóng, để một request bị ngắt giữa
   chừng vẫn để lại dấu vết,
3. draft được lập dưới uid **của chủ Station**, nên hạn mức, thư mục lưu trữ và
   lịch sử TX của Station vẫn nhất quán với một lần phát do chủ tự thực hiện.

Phía console (`prana_core/console/tx_phase.py`, port từ
`apps/android/lib/runtime/vhf/tx_controller.dart`) giữ đủ mọi quy tắc an toàn:

- `X-Request-ID` làm khoá idempotency; lỗi mạng **khôi phục bằng GET draft**,
  tuyệt đối không upload mù lần nữa,
- **không bao giờ tự phát lại** một lần phát thất bại; và khi Station biến mất
  giữa lúc đang phát, chỉ cho retry sau khi server đã chốt draft thành `failed`
  (nó có thể đã thực sự lên sóng),
- điều kiện tiên quyết: online + running + `ptt_ready` + không có lệnh đang bay
  + **đang giữ lease**,
- hộp thoại xác nhận nêu rõ tên Station và email chủ sở hữu, hỏi **một lần mỗi
  lần gắn** — không phải mỗi lần phát: một hộp thoại lặp lại sẽ bị bấm qua mà
  không đọc, tệ hơn là không có.

Cưỡng chế chiếm quyền **không cắt ngang** một lần phát đang diễn ra: lease được
cấp, nhưng điều kiện TX từ chối bằng `409 TX_BUSY` khi còn job của người khác.

## Rủi ro đã biết

**Quyền đọc transcript xuyên tenant là phần nguy hiểm nhất, không phải takeover.**
`prana_admin` được xây dựng có chủ đích với **zero** quyền đọc transcript; console
vượt qua ranh giới đó. Trước khi mở rộng số lượng operator, nên bổ sung:
`operator_scope` (`all | station_ids`), bắt buộc nhập lý do truy cập cho mọi
request trả về **nội dung**, và cho chủ Station thấy được dấu vết "bộ phận hỗ
trợ đã truy cập Station của bạn".

**`list_station_live_results` có một lỗi hẹp nhưng có thật** (`repository.py`):
`.limit(1000)` áp lên truy vấn `collection_group` **trước** bộ lọc tiền tố
`users/{uid}/...` chạy trong Python. Truy vấn sắp xếp `timestamp` giảm dần, nên
một lần chuyển chủ A→B **không** gây vấn đề: kết quả của B luôn mới hơn của A và
luôn nằm trong 1000 bản mới nhất.

Lỗi chỉ xuất hiện khi kết quả của chủ cũ lại **mới hơn** một phần kết quả của
chủ hiện tại trong cùng cửa sổ một ngày — tức Station bị chuyển đi rồi chuyển về
(A→B→A) trong ngày đó, và B tạo đủ nhiều kết quả để đẩy phần sớm hơn của A ra
khỏi 1000 bản mới nhất. Khi đó A mất phần kết quả buổi sáng của chính mình, âm
thầm, không có lỗi nào được báo.

Cách sửa: ghi `owner_uid` lên document kết quả và lọc phía server, để `limit`
áp sau khi đã loại kết quả của chủ khác.

## Giao diện: token, sáng/tối và thương hiệu

Desktop dùng chung ngôn ngữ thương hiệu với app Flutter nhưng giữ bố cục desktop.
Android có **hai** ngôn ngữ thị giác: bề mặt sản phẩm (`core/theme.dart`: canvas
nhạt, card có viền) và console Live VHF (`console_palette.dart`: ô phẳng phân cách
bằng hairline, không bo góc). Trên desktop, Fleet/Auth/Account/Plans theo bề mặt
sản phẩm; Station Workspace theo console.

- **Màu chỉ nằm ở `ui/theme.py`.** `styles.qss` là một `string.Template`; không
  viết hex literal vào đó, và không viết dấu đô-la-ngoặc-nhọn ngay cả trong
  comment — `substitute` sẽ coi nó là token. Test chặn cả hai.
- **Không `setStyleSheet` ở cấp widget.** Nó bị nướng cứng một màu và bỏ qua nút
  đổi theme. Màu thay đổi theo trạng thái đi qua dynamic property + luật QSS.
- **Icon là pixmap nướng cứng màu.** Dùng `bind_icon` (tự vẽ lại khi đổi theme),
  hoặc tự tạo lại icon trong handler `theme.changed` nếu glyph phụ thuộc trạng thái.
- **Dừng thu (hổ phách) khác phát sóng (đỏ).** Android dùng chung màu đỏ cho
  "STOP CAPTURE" và PTT đang giữ; desktop cố ý tách hai màu vì hậu quả khác hẳn nhau.
- Mọi cặp chữ/nền đạt WCAG AA ở cả hai theme; test tính tỉ lệ tương phản.
- Logo, icon `.ico`, ảnh installer và bản sao font đều sinh từ
  `tools/packaging/generate_brand_assets.py`. Đừng vẽ tay asset desktop riêng.
