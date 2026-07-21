# PRANA ELEX infrastructure

This Terraform stack creates Firebase/Identity Platform email and Google authentication,
Firestore, a 14-day Cloud Storage bucket, separate Cloud Run API/admin services,
IAP for the admin service and separate runtime/deployer identities. Firestore
Security Rules deny every Firebase client read/write; only server identities use IAM.

Runtime values such as billing IDs, images, user emails and credentials belong
in an untracked `terraform.tfvars`; copy `terraform.tfvars.example` to create it.
The Google provider Web client secret is sensitive and must exist only in that
ignored file and protected remote state. The Desktop OAuth client ID is public.
The Desktop OAuth client secret is stored separately in the existing Secret Manager
secret `prana-google-desktop-oauth-client-secret`; Terraform grants only the API
runtime service account access and injects its latest version into Cloud Run.

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
Before the final apply, create the OAuth consent screen plus separate Web and
Desktop OAuth clients in Google Auth Platform. Put their values in the ignored
`terraform.tfvars`; Terraform enables the Identity Platform Google provider with
the Web client. In the console, add the Desktop client ID to the provider's
external client IDs, because that list is not exposed by the Terraform resource.

After apply, copy the public `firebase_web_api_key`, `api_url` and
`google_desktop_oauth_client_id` outputs into both desktop build profiles. Never
copy `google_idp_web_client_secret` into client config or Git.

Set both global audio circuit-breaker variables to non-zero production values.
Budget notifications are alerts, not hard spending caps.

Google OAuth exchange is protected independently of client IP: each API instance
uses a bounded in-memory window and all instances share a fixed Firestore counter.
Tune `google_auth_instance_requests_per_minute` and
`google_auth_global_requests_per_minute` in the ignored environment tfvars when
traffic requirements change.
