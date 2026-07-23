# Kiến trúc PRANA ELEX

PRANA ELEX là monorepo gồm ba ứng dụng nền tảng, một core Python dùng chung và
hai dịch vụ Cloud Run.

## Ranh giới mã nguồn

```text
apps/windows      Qt Desktop + Windows Station + WASAPI + Credential Manager
apps/linux        Raspberry Pi Station headless + PulseAudio + Secret Service
apps/android      Flutter UI, Firebase Auth và Firestore realtime
       │
       └──────────── packages/prana_core
                     pipeline, VAD, API client, station protocol, storage

services/prana_api       Firebase-authenticated/station-signed public API
services/prana_admin     IAP-protected operator application
infra                    Firebase Rules và Terraform
```

`prana_core` không import app nền tảng, GUI toolkit hoặc audio implementation.
Core nhận `AudioBackend` và `CredentialStore` qua composition root của Windows
hoặc Linux. Windows chứa toàn bộ Qt UI; Linux không cài hoặc đóng gói PySide6,
qasync hay qtawesome.

## Runtime

- Windows Desktop dùng Firebase user session và Ed25519 device identity.
- Windows Station và Linux Station không giữ Firebase user session; chúng dùng
  Ed25519 station identity, poll desired state và gửi heartbeat/audio tới API.
- Android dùng REST cho mutation và Firestore listener cho trạng thái/kết quả.
- API/Admin là các deployment độc lập và không import client packages.

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

Entrypoint build ổn định ở root là `buildwin.bat`, `buildlinux` và
`buildapp.bat`. Logic và asset thật nằm cạnh từng app. Generated output,
credential, activation label và runtime storage không được commit.
