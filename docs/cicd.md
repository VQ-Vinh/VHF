# PRANA ELEX CI/CD

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

Tạo environment `staging-infra-plan` không có reviewer, chứa variables
`GCP_WIF_PROVIDER`, `GCP_TERRAFORM_SERVICE_ACCOUNT` và secret
`TFVARS_STAGING_B64`. Secret là base64 của `terraform.tfvars`; không dán tfvars
vào workflow hoặc commit.

Tạo environment `staging-infra` với required reviewer, chứa cùng hai variables
WIF/SA nhưng không cần tfvars secret. Job apply chỉ nhận saved plan.

Tạo environment `android-production` với required reviewer và secrets:

- `ANDROID_PRODUCTION_CONFIG_B64`
- `ANDROID_KEYSTORE_B64`
- `ANDROID_KEYSTORE_PASSWORD`
- `ANDROID_KEY_ALIAS`
- `ANDROID_KEY_PASSWORD`

Tạo environment `production` với required reviewer. Chỉ sau khi production đã
được kiểm thử đầy đủ mới cấu hình các variable `GCP_PRODUCTION_*`, staging image
reader variables và bật repository variable `PRODUCTION_CD_ENABLED=true`.

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

Staging/production deploy lưu revision hiện tại trước khi đổi traffic. Nếu
revision mới không Ready, không nhận 100% traffic, API health lỗi hoặc có error
log mới, workflow tự chuyển 100% traffic về revision cũ và kết thúc failed.

Rollback thủ công khẩn cấp:

```bash
gcloud run services update-traffic SERVICE \
  --project PROJECT --region REGION --to-revisions REVISION=100
```

Không rerun Terraform apply bằng một plan khác. Hủy lượt đang chờ approval và
dispatch workflow mới để tạo plan mới.
