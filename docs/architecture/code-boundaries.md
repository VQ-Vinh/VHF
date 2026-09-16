# Kiến trúc PRANA ELEX

PRANA ELEX là monorepo gồm ba ứng dụng nền tảng, một core Python dùng chung và
hai dịch vụ Cloud Run. Ứng dụng Flutter nhắm hai nền tảng di động: Android được
phát hành đầy đủ, iOS mới ở mức build và chạy Simulator trên CI.

## Ranh giới mã nguồn

```text
apps/windows      Qt Operator Console + Windows Station + WASAPI + Credential Manager
apps/linux        Raspberry Pi Station headless + ALSA/arecord + GPIO17 PTT
apps/android      Flutter UI, Firebase Auth và Firestore realtime
                  (android/ và ios/ là hai thư mục nền tảng của cùng app)
       │
       └──────────── packages/prana_core
                     pipeline, VAD, API client, station protocol, storage

services/prana_api       Firebase-authenticated/station-signed public API
                         (+ router /v1/operator/* cho Console)
services/prana_admin     IAP-protected operator application
                         (sở hữu/billing; cố ý mù với transcript)
infra                    Firebase Rules và Terraform
```

`prana_core` không import app nền tảng, GUI toolkit hoặc audio implementation.
`prana_core/console/` là tầng client của Operator Console (models, transport,
polling, máy trạng thái lệnh và TX) và cũng tuân thủ ranh giới đó: không Qt.
Core nhận `AudioBackend` và `CredentialStore` qua composition root của Windows
hoặc Linux. Windows chứa toàn bộ Qt UI; Linux không cài hoặc đóng gói PySide6,
qasync hay qtawesome.

## Runtime

- Windows Desktop là Operator Console: Firebase user session cộng cờ
  `fleet_operator` trên `users/{uid}`. Nó không còn chạy pipeline RX cục bộ;
  micro chỉ dùng cho TX. Console **chỉ dùng REST** và không bao giờ đọc
  Firestore trực tiếp, vì rules từ chối mọi read ngoài `users/{uid}` của chính
  nó — xem [operator-console.md](operator-console.md).
- Windows Station và Linux Station không giữ Firebase user session; chúng dùng
  Ed25519 station identity, poll desired state và gửi heartbeat/audio tới API.
- Android dùng REST cho mutation, Live/History/TX và Firestore projection cho
  trạng thái Station thuộc owner.
- API/Admin là các deployment độc lập và không import client packages.

RX và TX dùng worker riêng tại Station. Windows RX dùng WASAPI; Raspberry Pi RX
dùng ALSA qua tiến trình `arecord`, không dùng callback PortAudio. TX worker chỉ
claim khi Station running và PTT ready, pause riêng capture RX (không chờ các
request Gemini đang xử lý), kích PTT, phát final WAV rồi chỉ resume RX khi desired
state vẫn running. Raspberry Pi dùng GPIO17 active-high với key-up 400 ms, tail
300 ms và watchdog tuyệt đối 122 giây; Laptop dùng manual PTT. Hệ thống chưa có
channel-busy sensing.

Client không chứa service-account JSON và không gọi Vertex AI hoặc Cloud Storage
trực tiếp. Firebase Web API key/OAuth client ID trong Windows hoặc Android là
định danh public; mọi quyền nghiệp vụ vẫn cần Firebase token hoặc station signature.

## Build và môi trường

```text
.venv/dev          Windows/core development và Qt tests
.venv/backend      API/Admin tests
.venv/windows      PyInstaller/Inno Setup
.venv/linux-arm64  PyInstaller/Debian trên Raspberry Pi

build/buildwin/    Windows intermediate files
build/buildlinux/  Linux intermediate files
build/buildapp/    Android/Flutter intermediate files
installers/<platform> distributable artifacts
```

Entrypoint build đang dùng ở root là `build_android_apk.bat` và `buildlinux`.
Logic Windows vẫn nằm trong `apps/windows/` nhưng không có root wrapper trong
giai đoạn tập trung phát triển Android. Generated output,
credential, activation label và runtime storage không được commit.

## Android Station Workspace

Android composition lives in `apps/android/lib/app/di/`. SDK-free contracts/models live in `domain/`, API/Firestore/audio adapters in `data/`, and phone-side RX command/TX/speech lifecycle in `runtime/`. Runtime never imports feature UI. Station tabs observe one selected uid/Station session; remote capture and VAD remain in Python. Dashboard depends on `TelemetryRepository`, injected with a mock implementation; it has no desired-state/hardware control.

The [per-file migration and validation record](android-workspace-migration.md) documents ownership and current evidence.
