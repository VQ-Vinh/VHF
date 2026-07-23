# PRANA ELEX installers

Thư mục này chỉ chứa artifact phát hành được tạo bởi các lệnh build:

- `windows/`: bộ cài Inno Setup `.exe`.
- `linux/`: gói Raspberry Pi `.deb` và checksum `.sha256`.
- `android/staging/` và `android/production/`: APK/AAB theo flavor.

Các file trong thư mục này là output sinh tự động, không commit vào Git và không
chứa credential, keystore, runtime storage hoặc activation secret.
