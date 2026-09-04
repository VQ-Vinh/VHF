# PRANA ELEX CI/CD

## Change detection và required gate

Job `changes` tính phạm vi thay đổi từ base/head SHA thật của sự kiện bằng
`tools/ci/changed_components.py`. Với base SHA bằng zero, commit không tồn tại
hoặc path không nhận diện được, helper chọn phương án an toàn là chạy toàn bộ
CI. PR chỉ sửa tài liệu vẫn chạy `quality` và `CI / gate`; các job subsystem có
thể `skipped` nhưng `gate` vẫn là required check duy nhất.

Trên push vào `main`, CI xuất artifact `deploy-selection` giữ một ngày. Workflow
staging chỉ tin artifact của đúng `workflow_run.id`, đồng thời xác minh
`head_sha` khớp commit đã qua gate trước khi chọn API/Admin để deploy.

Backend được kiểm tra trên Python 3.11 và 3.12. Khi service thay đổi, CI build
Dockerfile production, smoke-test `/health`, tạo SBOM CycloneDX và scan image;
vulnerability `CRITICAL` có bản vá làm gate thất bại.

## Luồng phát hành

- Pull Request và push `main`: chạy `CI / gate` gồm Python, Windows, Linux,
  Flutter, Terraform, dependency review và secret scan.
- CI thành công trên `main`: chỉ API/Admin có source thay đổi được build, push
  bằng tag commit SHA và deploy staging theo image digest.
- Terraform staging: chạy thủ công workflow `Terraform staging`; plan không
  chứa plaintext tfvars, apply chờ approval và dùng đúng plan artifact.
- Android: tag `vX.Y.Z` chờ approval, build APK/AAB production đã ký và phát
  hành cùng `SHA256SUMS`.
- Production: workflow tồn tại nhưng bị khóa khi
  `PRODUCTION_CD_ENABLED != true`.

Android release chỉ đọc signing secrets sau khi tag `vX.Y.Z` được xác minh thuộc
lịch sử `main` và commit tag có check `gate` thành công. Production promotion yêu
cầu đủ `service`, image `digest` và `source_sha`; workflow đối chiếu tag commit,
digest từng repository, digest từng được staging sử dụng, rồi xác minh chữ ký
keyless từ workflow staging trên `main`.

Image staging được build với provenance tối đa, SBOM và OCI labels, sau đó ký
theo digest bằng GitHub OIDC. Vì vậy image được tạo trước khi cơ chế ký này có
hiệu lực sẽ không thể promote bằng workflow production mới.

Cloud Build YAML vẫn là fallback thủ công. Không dùng nó song song với một lượt
GitHub Actions đang deploy cùng service.

## Bootstrap Google OIDC

Một quản trị viên chạy Terraform staging lần đầu bằng credential tin cậy:

```powershell
cd infra\terraform
terraform init
terraform plan -out=github-oidc.tfplan
terraform apply github-oidc.tfplan
terraform output
```

Plan tạo Workload Identity Provider và ba service account:

- `prana-deployer`: chỉ subject của branch `main`, push Artifact Registry và
  deploy Cloud Run staging.
- `prana-terraform`: chỉ hai environment `staging-infra-plan` và
  `staging-infra`.
- `prana-release-reader`: chỉ environment `production`, đọc image staging để
  promote đúng digest.

Không tạo hoặc tải service-account key JSON.

## GitHub variables, secrets và environments

Repository variables dùng cho staging tự động:

| Variable | Giá trị staging |
| --- | --- |
| `GCP_STAGING_PROJECT_ID` | Google Cloud project ID |
| `GCP_REGION` | `us-central1` |
| `GCP_ARTIFACT_REPOSITORY` | `prana-elex` |
| `GCP_WIF_PROVIDER` | Terraform output `github_workload_identity_provider` |
| `GCP_DEPLOYER_SERVICE_ACCOUNT` | Terraform output `github_deployer_service_account` |
| `STAGING_CD_ENABLED` | Đặt `true` sau khi đã cấu hình đủ các variable ở trên |

Tạo environment `staging-infra-plan` không có reviewer, chứa variables
`GCP_WIF_PROVIDER`, `GCP_TERRAFORM_SERVICE_ACCOUNT` và secret
`TFVARS_STAGING_B64`. Secret là base64 của `terraform.tfvars`; không dán tfvars
vào workflow hoặc commit.

Tạo thêm secret `TFPLAN_ENCRYPTION_KEY` có cùng giá trị ngẫu nhiên tối thiểu 32
ký tự trong cả `staging-infra-plan` và `staging-infra`. Workflow chỉ upload
`staging.tfplan.gpg`; plaintext tfvars, plan và key tạm được xóa trước khi kết
thúc job. Thiếu hoặc sai key phải làm workflow fail, không được tạo plan mới ở
job apply.

Tạo environment `staging-infra` với required reviewer, chứa cùng hai variables
WIF/SA và `TFPLAN_ENCRYPTION_KEY`, nhưng không cần tfvars secret. Job apply chỉ
giải mã và áp dụng saved plan đã được duyệt.

Tạo environment `android-production` với required reviewer và secrets:

- `ANDROID_PRODUCTION_CONFIG_B64`
- `ANDROID_KEYSTORE_B64`
- `ANDROID_KEYSTORE_PASSWORD`
- `ANDROID_KEY_ALIAS`
- `ANDROID_KEY_PASSWORD`

Tạo environment `production` với required reviewer. Chỉ sau khi production đã
được kiểm thử đầy đủ mới cấu hình các variable `GCP_PRODUCTION_*`, staging image
reader variables và bật repository variable `PRODUCTION_CD_ENABLED=true`.

Trước khi bật production validation mới, apply Terraform staging để principal
`prana-release-reader` nhận quyền tối thiểu `roles/run.viewer`; quyền này chỉ dùng
để đối chiếu digest của revision Cloud Run staging.

## Branch protection

Sau khi workflow CI xuất hiện trên GitHub, bảo vệ `main`:

- require Pull Request;
- require status check `CI / gate` và require branch up to date;
- block force push và branch deletion;
- do not allow bypass, kể cả administrator;
- không yêu cầu review count để chủ repository có thể merge sau khi checks đạt.

Không bật protection trước khi `CI / gate` đã chạy ít nhất một lần, nếu không
GitHub có thể chưa nhận diện được tên check.

## Rollback và xử lý lỗi

Composite action deploy luôn tạo revision mới với `--no-traffic`, chờ đúng
revision đạt Ready rồi mới chuyển traffic bằng tên revision cụ thể. Trước deploy,
workflow lưu toàn bộ traffic map; mọi lỗi readiness, traffic, health hoặc log đều
kích hoạt khôi phục đúng các tỷ lệ trước đó. Nếu rollback cũng lỗi, job vẫn fail
và ghi cảnh báo vào GitHub Step Summary.

Nếu revision mới không Ready, không nhận 100% traffic, API health lỗi hoặc có
error log mới, workflow khôi phục traffic map trước đó và kết thúc failed.

Rollback thủ công khẩn cấp:

```bash
gcloud run services update-traffic SERVICE \
  --project PROJECT --region REGION --to-revisions REVISION=100
```

Không rerun Terraform apply bằng một plan khác. Hủy lượt đang chờ approval và
dispatch workflow mới để tạo plan mới.
