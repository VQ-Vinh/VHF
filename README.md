# PRANA ELEX 1.1

PRANA ELEX thu âm VHF, tách đoạn giọng nói và dịch theo thời gian thực trên
Windows 10/11 x64 hoặc Raspberry Pi 4B Bookworm ARM64.

Từ phiên bản 1.1, ứng dụng là client SaaS. Máy người dùng **không gọi Google
Cloud trực tiếp**, không cần Google Account và không nhận service-account JSON:

```text
Windows / Raspberry Pi
  ├─ Audio capture, VAD, UI, WAV/result local
  └─ Firebase user token + Ed25519 device signature
                 │ HTTPS
                 ▼
        Cloud Run: prana-api
          ├─ subscription, device, rate/quota, idempotency (Firestore)
          ├─ Gemini on Vertex AI bằng Cloud Run service identity (ADC)
          └─ WAV + result JSON trong GCS, lifecycle xóa sau 14 ngày

        Cloud Run: prana-admin
          └─ IAP, plan/subscription/device/audit dành cho Bên A
```

Prompt, parser, model configuration, GCS path và Google IAM chỉ tồn tại ở
backend. Firebase Web API key trong client là định danh public của Firebase app;
nó không cấp quyền Google Cloud và không thay thế Firebase ID token.

## Cấu trúc chính

```text
src/prana_elex/                 Desktop/Pi client
services/prana_api/             FastAPI public business API
services/prana_admin/           IAP-protected operator web app
infra/terraform/                Production Google Cloud infrastructure
scripts/packaging/windows/      Windows build + Inno Setup
scripts/packaging/linux-arm64/  Pi 4B build + Debian package
config/profiles/                Public build configuration per platform
tests/client/                   Desktop/Pi client and Qt tests
tests/api/                      PRANA API tests
tests/admin/                    PRANA Admin tests
tests/packaging/                Build and release validation tests
```

Chi tiết ranh giới và chiều phụ thuộc: [`docs/architecture.md`](docs/architecture.md).

## Luồng tài khoản

1. Windows chọn data folder trong installer; Linux/source chọn trong trang Data Setup
   tích hợp. Người dùng tạo tài khoản bằng email/password và xác minh email ngay
   trong cửa sổ PRANA ELEX.
2. Sau khi xác minh email, backend tự động kích hoạt gói Free với 10 phút audio
   mỗi ngày UTC. Không cần Admin duyệt. Plus (60 phút/ngày) và Pro (180
   phút/ngày) được hiển thị trong app ở trạng thái sắp phát hành.
3. Người dùng đăng nhập. App tự chuyển giữa Login, Account Center và Translation
   trong cùng một cửa sổ. Account Center cho phép xem/chọn gói, usage ngày, thiết bị, gửi
   email đặt lại mật khẩu và đăng xuất. Refresh token được lưu bằng Windows Credential Manager
   hoặc Secret Service; Raspberry Pi có fallback file `0600`. Mật khẩu không được lưu.
4. Mỗi installation sinh một Ed25519 private key riêng, không export qua UI. Một
   tài khoản có tối đa hai thiết bị active.
5. Mỗi WAV dùng một `request_id` ổn định. Retry cùng nội dung không gọi Gemini và
   không tính quota lần hai.

Admin vẫn có thể suspend/reactivate tài khoản nhưng không cấp gói thủ công.
Chưa tích hợp cổng thanh toán; Plus và Pro không thể đăng ký ở client hoặc API.

## Chạy client từ source

Yêu cầu Python 3.11+ và các thư viện audio tương ứng hệ điều hành:

```cmd
scripts\setup\setup.bat
run_dev.bat
```

CLI trên Windows:

```cmd
scripts\dev\run-cli.bat
scripts\dev\run-cli.bat -t vi batch path\recording.wav
```

Trên Pi:

```bash
./scripts/setup/setup.sh
./scripts/dev/run-dev.sh
./scripts/dev/run-cli.sh -t en batch recording.wav
```

Trước khi đăng nhập, cấu hình hai giá trị public trong `config/default.toml` khi
chạy source; cấu hình cả hai file trong `config/profiles/` trước khi build release:

```toml
[backend]
api_url = "https://prana-api-....run.app"
firebase_api_key = "Firebase Web API key"
google_oauth_client_id = "Google Desktop OAuth client ID ending in .apps.googleusercontent.com"
timeout_seconds = 150
```

`google_oauth_client_id` là định danh public, không phải client secret. Nếu để trống
khi chạy source, nút Google sẽ được ẩn; release build bắt buộc phải có client ID hợp
lệ. Không đặt Google credential, OAuth client secret, JSON key hoặc biến
`GOOGLE_APPLICATION_CREDENTIALS` trên máy client.

## Chạy backend local

Backend production dùng ADC. Với development, đăng nhập bằng Google user hoặc
service-account impersonation; không tạo JSON key:

```bash
python -m venv .venv/backend
.venv/backend/bin/pip install -r services/prana_api/requirements.txt
gcloud auth application-default login

export PRANA_API_GOOGLE_CLOUD_PROJECT=your-dev-project
export PRANA_API_FIREBASE_PROJECT_ID=your-dev-project
export PRANA_API_STORAGE_BUCKET=your-dev-bucket
uvicorn services.prana_api.main:app --reload --port 8080
```

Windows PowerShell dùng `.venv\backend\Scripts\python.exe` và `$env:...` tương
ứng. Admin local yêu cầu giả lập header IAP chỉ trong môi trường development;
production luôn bật Cloud Run IAP và allowlist email:

```bash
pip install -r services/prana_admin/requirements.txt
export PRANA_ADMIN_ENV=development
export PRANA_ADMIN_DEV_EMAIL=technical@example.com
uvicorn services.prana_admin.main:app --port 8081
```

PowerShell dùng `$env:PRANA_ADMIN_ENV="development"` và
`$env:PRANA_ADMIN_DEV_EMAIL="technical@example.com"`. Bypass này tự vô hiệu khi
biến Cloud Run `K_SERVICE` tồn tại; production vẫn bắt buộc IAP.

Web admin dùng giao diện responsive tại `/`, danh sách có lọc/phân trang tại
`/users` và hỗ trợ English/Vietnamese bằng bộ chọn ở góc trên. Trước lần deploy
đầu tiên có trường tìm kiếm chuẩn hóa, chạy dry-run rồi mới backfill:

```powershell
.venv\backend\Scripts\python.exe scripts\setup\backfill_admin_search.py --project PROJECT_ID
.venv\backend\Scripts\python.exe scripts\setup\backfill_admin_search.py --project PROJECT_ID --apply
```

Các Firestore composite index phục vụ bộ lọc admin được quản lý bằng Terraform;
kiểm tra bằng `terraform plan` trước khi apply.

API client:

- `GET /v1/me`, `GET /v1/usage`
- `GET /v1/devices`, `POST /v1/devices/register`
- `DELETE /v1/devices/{id}`
- `POST /v1/audio/process`

`audio/process` nhận WAV mono 16 kHz PCM16 tối đa 120 giây/10 MiB, Firebase ID
token, device ID, timestamp và chữ ký Ed25519. Plan quyết định phút/ngày UTC, RPM,
concurrency và số thiết bị. Firestore transaction reserve quota trước Gemini và
settle sau xử lý.

Tài khoản đã xác minh được xem và revoke thiết bị ngay cả khi gói hết hạn hoặc
bị tạm khóa; đăng ký thiết bị mới và xử lý audio vẫn yêu cầu subscription active.

## Hạ tầng production

Sao chép example và điền giá trị production (file thật bị `.gitignore`):

```bash
cd infra/terraform
cp terraform.tfvars.example terraform.tfvars
terraform init
terraform plan
terraform apply
```

Stack tạo Firebase/Identity Platform, Firestore, bucket Standard không versioning,
soft delete tắt và lifecycle 14 ngày, Artifact Registry, hai Cloud Run service,
IAP, budget alerts, runtime/admin/deployer service accounts và least-privilege IAM.
Nếu có Organization, hai policy cấm tạo/upload service-account key cũng được áp
dụng. Các global circuit breaker phải đặt giá trị khác 0 trước production.

Lần đầu cần bootstrap API và Artifact Registry trước khi image Cloud Run tồn tại:

```bash
terraform apply -target=google_project_service.apis -target=google_artifact_registry_repository.containers
gcloud auth configure-docker us-central1-docker.pkg.dev
docker build -f services/prana_api/Dockerfile -t us-central1-docker.pkg.dev/PROJECT/prana-elex/prana-api:1.1.0 .
docker push us-central1-docker.pkg.dev/PROJECT/prana-elex/prana-api:1.1.0
docker build -f services/prana_admin/Dockerfile -t us-central1-docker.pkg.dev/PROJECT/prana-elex/prana-admin:1.1.0 .
docker push us-central1-docker.pkg.dev/PROJECT/prana-elex/prana-admin:1.1.0
terraform apply
```

Sau `apply`, đưa output `firebase_web_api_key`, `api_url` và
`google_desktop_oauth_client_id` vào hai build profile.

### Cấu hình Google sign-in

Google sign-in dùng Authorization Code + PKCE và callback loopback
`127.0.0.1`; ứng dụng mở trình duyệt hệ thống, không nhúng trình duyệt. App gửi
authorization code và PKCE verifier qua HTTPS cho PRANA API. Cloud Run đọc Desktop
client secret từ Secret Manager, đổi code lấy Google token rồi đổi ngay sang Firebase
session. App chỉ lưu Firebase refresh token; Google token và Desktop secret không được
trả về hoặc đóng gói trong client. Cấu hình staging theo thứ tự:

1. Trong Google Auth Platform, cấu hình consent screen loại External, trạng thái
   Testing và thêm email QA vào Test users.
2. Tạo một OAuth client loại Web application cho Identity Platform và một OAuth
   client loại Desktop app dùng chung cho Windows/Pi.
3. Ghi Web client ID/secret và public Desktop client ID vào file
   `infra/terraform/terraform.tfvars` bị ignore, sau đó chạy `terraform plan` và
   `terraform apply`.
4. Trong Identity Platform/Firebase Authentication > Sign-in method > Google, thêm
   Desktop client ID vào danh sách OAuth client IDs từ project bên ngoài (external
   client IDs). Terraform provider chưa quản lý trường danh sách này nên đây là bước
   console có chủ đích.
5. Chép Desktop client ID public vào `backend.google_oauth_client_id` của config
   source và hai build profile. Không chép Web client secret vào app.
6. Tạo Secret Manager secret `prana-google-desktop-oauth-client-secret` chứa Desktop
   client secret. Chỉ `prana-api-runtime` được cấp `secretAccessor`; không đưa giá trị
   secret vào Terraform state hoặc repository.

Production phải dùng bộ OAuth clients riêng và publish consent screen trước khi mở
cho mọi tài khoản Gmail/Google Workspace.

Terraform không chứa project ID, billing account, admin email hoặc credential
thật. Lần bật IAP đầu tiên ở project không thuộc Organization có thể cần hoàn tất
OAuth consent trong Google Cloud Console.

## Build ứng dụng

Windows 10/11 x64 (chạy trên Windows):

```cmd
buildwin.bat
```

Artifact:

```text
dist/windows/PRANA_ELEX/PRANA_ELEX.exe
release/windows/PRANA_ELEX_Setup_1.1.0_x64.exe
```

Windows installer hỗ trợ English và Tiếng Việt, dùng chung icon nhận diện với
ứng dụng và yêu cầu chọn Data folder trước khi cài. Dữ liệu trong thư mục này
được giữ nguyên khi gỡ ứng dụng.

Raspberry Pi 4B, Raspberry Pi OS Desktop Bookworm 64-bit (chạy trực tiếp trên Pi):

```bash
./buildlinux
sudo apt install ./release/linux-arm64/prana-elex_1.1.0_arm64.deb
```

Linux không dùng `.exe`; artifact phân phối là
`release/linux-arm64/prana-elex_1.1.0_arm64.deb`. `build.bat` chỉ là alias tạm
cho `buildwin.bat`.

## Dữ liệu và gỡ cài đặt

- Windows mặc định: thư mục người dùng chọn trong installer.
- Pi mặc định: `~/PRANA_ELEX_Data`.
- Audio/result local được lưu trực tiếp tại:
  `<data folder>/VHF_Storage/audio|results`.
- Sign out chỉ xóa phiên local và trở về Login; không đóng app, không revoke thiết
  bị và không xóa dữ liệu. Layout cũ trong `accounts/<firebase_uid>` được chuyển
  về Data folder đã chọn khi tài khoản đó đăng nhập.
- Settings Pi: `~/.config/prana-elex/settings.json`.
- Token/device identity: OS credential store; fallback Pi
  `~/.config/prana-elex/auth.json` mode `0600`.
- Cloud: `customers/{uid}/{yyyy}/{mm}/{dd}/{session_id}/{request_id}.wav|json`.

Cloud lifecycle xóa object sau 14 ngày. Ứng dụng không tự xóa WAV local theo
retention cloud. `apt remove` giữ settings, token và dữ liệu người dùng.

## Kiểm thử

```powershell
$env:PYTHONPATH="src;."
.venv\backend\Scripts\python.exe -m unittest discover -s tests -t . -v
.venv\backend\Scripts\python.exe -m compileall -q src services tests
```

Test Qt chạy bằng development environment:

```powershell
$env:PYTHONPATH="src;."
$env:QT_QPA_PLATFORM="offscreen"
.venv\dev\Scripts\python.exe -m unittest tests.client.test_account_shell -v
```

Trước release cần chạy thêm Terraform validation, build/validator từng platform,
test Firebase/Firestore emulator và end-to-end trên Windows/Pi với project staging.
Release validator từ chối service-account JSON, private key, token/settings runtime,
PFX và dữ liệu VHF.
