# PRANA ELEX infrastructure

This Terraform stack creates Firebase/Identity Platform email authentication,
Firestore, a 14-day Cloud Storage bucket, separate Cloud Run API/admin services,
IAP for the admin service and separate runtime/deployer identities. Firestore
Security Rules deny every Firebase client read/write; only server identities use IAM.

Runtime values such as billing IDs, images, user emails and credentials belong
in an untracked `terraform.tfvars`; copy `terraform.tfvars.example` to create it.

## Terraform state

The staging state uses the dedicated, externally bootstrapped GCS bucket
`prana-elex-staging-2816-tfstate` and the `terraform/staging` prefix configured
in `backend.tf`. The state bucket is deliberately separate from the customer
recordings bucket and from this stack's lifecycle. It has uniform bucket-level
access, public access prevention, object versioning and soft delete enabled.
Grant `roles/storage.objectAdmin` on this bucket only to Terraform operators;
the API and admin runtime service accounts must not have state access.

Use a different bucket and prefix when creating production infrastructure.
Backend configuration cannot use Terraform input variables, so update or
replace `backend.tf`, then run `terraform init -migrate-state` deliberately.
Never use `-reconfigure` when the intention is to move existing state.

## Deploy

Bootstrap the APIs/repository, build and push both images, then apply the
complete stack:

```bash
terraform init
terraform apply -target=google_project_service.apis -target=google_artifact_registry_repository.containers
gcloud auth configure-docker us-central1-docker.pkg.dev
docker build -f ../../services/prana_api/Dockerfile -t API_IMAGE ../..
docker push API_IMAGE
docker build -f ../../services/prana_admin/Dockerfile -t ADMIN_IMAGE ../..
docker push ADMIN_IMAGE
terraform plan
terraform apply
```

The first IAP enablement for a project without an Organization may require the
Google Cloud console because its OAuth client cannot be created programmatically.
After apply, copy the public `firebase_web_api_key` and `api_url` outputs into
both desktop build profiles.

Set both global audio circuit-breaker variables to non-zero production values.
Budget notifications are alerts, not hard spending caps.
