locals {
  services = toset([
    "aiplatform.googleapis.com",
    "artifactregistry.googleapis.com",
    "billingbudgets.googleapis.com",
    "cloudbuild.googleapis.com",
    "cloudresourcemanager.googleapis.com",
    "firestore.googleapis.com",
    "firebase.googleapis.com",
    "firebaserules.googleapis.com",
    "identitytoolkit.googleapis.com",
    "iap.googleapis.com",
    "iam.googleapis.com",
    "orgpolicy.googleapis.com",
    "run.googleapis.com",
    "storage.googleapis.com",
  ])
}

data "google_project" "current" {}

resource "google_project_service_identity" "iap" {
  provider   = google-beta
  project    = var.project_id
  service    = "iap.googleapis.com"
  depends_on = [google_project_service.apis]
}

resource "google_project_service" "apis" {
  for_each           = local.services
  service            = each.value
  disable_on_destroy = false
}

resource "google_firebase_project" "production" {
  project    = var.project_id
  provider   = google-beta
  depends_on = [google_project_service.apis, google_project_iam_member.terraform_firebase_admin]
}

resource "google_project_iam_member" "terraform_firebase_admin" {
  project = var.project_id
  role    = "roles/firebase.admin"
  member  = var.terraform_operator
}

resource "google_identity_platform_config" "auth" {
  project = var.project_id
  sign_in {
    email {
      enabled           = true
      password_required = true
    }
    phone_number {
      enabled = false
    }
  }
  depends_on = [google_firebase_project.production]
}

resource "google_firebase_web_app" "desktop" {
  provider        = google-beta
  project         = var.project_id
  display_name    = "PRANA ELEX Desktop"
  deletion_policy = "ABANDON"
  depends_on      = [google_firebase_project.production]
}

data "google_firebase_web_app_config" "desktop" {
  provider   = google-beta
  project    = var.project_id
  web_app_id = google_firebase_web_app.desktop.app_id
}

resource "google_firestore_database" "production" {
  project                 = var.project_id
  name                    = "(default)"
  location_id             = var.region
  type                    = "FIRESTORE_NATIVE"
  delete_protection_state = "DELETE_PROTECTION_ENABLED"
  deletion_policy         = "ABANDON"
  depends_on              = [google_project_service.apis]
}

resource "google_firestore_field" "rate_limit_ttl" {
  project    = var.project_id
  database   = google_firestore_database.production.name
  collection = "rate_minutes"
  field      = "expires_at"
  ttl_config {}
}

resource "google_firestore_index" "users_status_email" {
  project     = var.project_id
  database    = google_firestore_database.production.name
  collection  = "users"
  query_scope = "COLLECTION"
  fields {
    field_path = "status"
    order      = "ASCENDING"
  }
  fields {
    field_path = "email_lower"
    order      = "ASCENDING"
  }
}

resource "google_firestore_index" "users_plan_email" {
  project     = var.project_id
  database    = google_firestore_database.production.name
  collection  = "users"
  query_scope = "COLLECTION"
  fields {
    field_path = "plan_id"
    order      = "ASCENDING"
  }
  fields {
    field_path = "email_lower"
    order      = "ASCENDING"
  }
}

resource "google_firestore_index" "users_status_plan_email" {
  project     = var.project_id
  database    = google_firestore_database.production.name
  collection  = "users"
  query_scope = "COLLECTION"
  fields {
    field_path = "status"
    order      = "ASCENDING"
  }
  fields {
    field_path = "plan_id"
    order      = "ASCENDING"
  }
  fields {
    field_path = "email_lower"
    order      = "ASCENDING"
  }
}

resource "google_firestore_index" "users_status_plan" {
  project     = var.project_id
  database    = google_firestore_database.production.name
  collection  = "users"
  query_scope = "COLLECTION"
  fields {
    field_path = "status"
    order      = "ASCENDING"
  }
  fields {
    field_path = "plan_id"
    order      = "ASCENDING"
  }
}

resource "google_firebaserules_ruleset" "firestore_deny_client" {
  project = var.project_id
  source {
    files {
      name    = "firestore.rules"
      content = file("${path.module}/../firebase/firestore.rules")
    }
  }
  depends_on = [google_project_service.apis]
}

resource "google_firebaserules_release" "firestore" {
  project      = var.project_id
  name         = "cloud.firestore"
  ruleset_name = google_firebaserules_ruleset.firestore_deny_client.name
}

resource "google_storage_bucket" "recordings" {
  name                        = var.bucket_name
  location                    = "US-CENTRAL1"
  storage_class               = "STANDARD"
  uniform_bucket_level_access = true
  public_access_prevention    = "enforced"
  versioning { enabled = false }
  soft_delete_policy { retention_duration_seconds = 0 }
  lifecycle_rule {
    condition { age = 14 }
    action { type = "Delete" }
  }
}

resource "google_artifact_registry_repository" "containers" {
  location      = var.region
  repository_id = "prana-elex"
  format        = "DOCKER"
  depends_on    = [google_project_service.apis]
}

resource "google_service_account" "api_runtime" {
  account_id   = "prana-api-runtime"
  display_name = "PRANA API Cloud Run runtime"
}

resource "google_service_account" "admin_runtime" {
  account_id   = "prana-admin-runtime"
  display_name = "PRANA Admin Cloud Run runtime"
}

resource "google_service_account" "deployer" {
  account_id   = "prana-deployer"
  display_name = "PRANA CI deployer"
}

resource "google_project_iam_member" "api_vertex" {
  project = var.project_id
  role    = "roles/aiplatform.user"
  member  = google_service_account.api_runtime.member
}

resource "google_project_iam_member" "api_firestore" {
  project = var.project_id
  role    = "roles/datastore.user"
  member  = google_service_account.api_runtime.member
}

resource "google_project_iam_member" "api_firebase_auth" {
  project = var.project_id
  role    = "roles/firebaseauth.viewer"
  member  = google_service_account.api_runtime.member
}

resource "google_project_iam_member" "admin_firestore" {
  project = var.project_id
  role    = "roles/datastore.user"
  member  = google_service_account.admin_runtime.member
}

resource "google_storage_bucket_iam_member" "api_objects" {
  bucket = google_storage_bucket.recordings.name
  role   = "roles/storage.objectAdmin"
  member = google_service_account.api_runtime.member
}

resource "google_artifact_registry_repository_iam_member" "deployer_images" {
  location   = google_artifact_registry_repository.containers.location
  repository = google_artifact_registry_repository.containers.name
  role       = "roles/artifactregistry.writer"
  member     = google_service_account.deployer.member
}

resource "google_project_iam_member" "deployer_run" {
  project = var.project_id
  role    = "roles/run.admin"
  member  = google_service_account.deployer.member
}

resource "google_service_account_iam_member" "deployer_uses_api" {
  service_account_id = google_service_account.api_runtime.name
  role               = "roles/iam.serviceAccountUser"
  member             = google_service_account.deployer.member
}

resource "google_service_account_iam_member" "deployer_uses_admin" {
  service_account_id = google_service_account.admin_runtime.name
  role               = "roles/iam.serviceAccountUser"
  member             = google_service_account.deployer.member
}

resource "google_cloud_run_v2_service" "api" {
  count                = var.deploy_services ? 1 : 0
  name                 = "prana-api"
  location             = var.region
  deletion_protection  = true
  ingress              = "INGRESS_TRAFFIC_ALL"
  invoker_iam_disabled = true
  template {
    service_account                  = google_service_account.api_runtime.email
    timeout                          = "180s"
    max_instance_request_concurrency = 20
    scaling { max_instance_count = var.api_max_instance_count }
    containers {
      image = var.api_image
      resources { limits = { cpu = "2", memory = "2Gi" } }
      env {
        name  = "PRANA_API_ENVIRONMENT"
        value = var.environment
      }
      env {
        name  = "PRANA_API_RUNTIME_IMAGE"
        value = var.api_image
      }
      env {
        name  = "PRANA_API_GOOGLE_CLOUD_PROJECT"
        value = var.project_id
      }
      env {
        name  = "PRANA_API_FIREBASE_PROJECT_ID"
        value = var.project_id
      }
      env {
        name  = "PRANA_API_GOOGLE_CLOUD_LOCATION"
        value = var.region
      }
      env {
        name  = "PRANA_API_STORAGE_BUCKET"
        value = google_storage_bucket.recordings.name
      }
      env {
        name  = "PRANA_API_GLOBAL_DAILY_AUDIO_SECONDS"
        value = tostring(var.global_daily_audio_seconds)
      }
      env {
        name  = "PRANA_API_GLOBAL_MONTHLY_AUDIO_SECONDS"
        value = tostring(var.global_monthly_audio_seconds)
      }
      env {
        name  = "PRANA_API_INPUT_COST_PER_MILLION_TOKENS"
        value = tostring(var.input_cost_per_million_tokens)
      }
      env {
        name  = "PRANA_API_OUTPUT_COST_PER_MILLION_TOKENS"
        value = tostring(var.output_cost_per_million_tokens)
      }
    }
  }
  depends_on = [google_project_service.apis]
}

resource "google_cloud_run_v2_service" "admin" {
  count               = var.deploy_services ? 1 : 0
  name                = "prana-admin"
  location            = var.region
  deletion_protection = true
  ingress             = "INGRESS_TRAFFIC_ALL"
  iap_enabled         = true
  template {
    service_account = google_service_account.admin_runtime.email
    scaling { max_instance_count = var.admin_max_instance_count }
    containers {
      image = var.admin_image
      resources { limits = { cpu = "1", memory = "512Mi" } }
      env {
        name  = "GOOGLE_CLOUD_PROJECT"
        value = var.project_id
      }
      env {
        name  = "PRANA_ADMIN_ALLOWED_EMAILS"
        value = join(",", var.admin_emails)
      }
    }
  }
  depends_on = [google_project_service.apis]
}

resource "google_cloud_run_v2_service_iam_member" "iap_invoker" {
  count    = var.deploy_services ? 1 : 0
  project  = var.project_id
  location = var.region
  name     = google_cloud_run_v2_service.admin[0].name
  role     = "roles/run.invoker"
  member   = google_project_service_identity.iap.member
}

resource "google_iap_web_cloud_run_service_iam_member" "admin_access" {
  for_each               = var.deploy_services ? var.admin_members : toset([])
  project                = var.project_id
  location               = var.region
  cloud_run_service_name = google_cloud_run_v2_service.admin[0].name
  role                   = "roles/iap.httpsResourceAccessor"
  member                 = each.value
}

resource "google_billing_budget" "production" {
  billing_account = var.billing_account
  display_name    = "PRANA ELEX ${var.environment}"
  budget_filter { projects = ["projects/${data.google_project.current.number}"] }
  amount {
    specified_amount {
      currency_code = var.budget_currency_code
      units         = tostring(var.monthly_budget_amount)
    }
  }
  threshold_rules { threshold_percent = 0.5 }
  threshold_rules { threshold_percent = 0.8 }
  threshold_rules { threshold_percent = 1.0 }
}

resource "google_org_policy_policy" "disable_key_creation" {
  count  = var.manage_project_key_policies ? 1 : 0
  name   = "projects/${data.google_project.current.number}/policies/iam.managed.disableServiceAccountKeyCreation"
  parent = "projects/${data.google_project.current.number}"
  spec {
    rules {
      enforce = "TRUE"
    }
  }
}

resource "google_org_policy_policy" "disable_key_upload" {
  count  = var.manage_project_key_policies ? 1 : 0
  name   = "projects/${data.google_project.current.number}/policies/iam.disableServiceAccountKeyUpload"
  parent = "projects/${data.google_project.current.number}"
  spec {
    rules {
      enforce = "TRUE"
    }
  }
}
