variable "project_id" { type = string }
variable "environment" {
  type = string
  validation {
    condition     = contains(["staging", "production"], var.environment)
    error_message = "Environment must be staging or production."
  }
}
variable "deploy_services" {
  type        = bool
  default     = false
  description = "Create Cloud Run services only after their images have been pushed."
}
variable "region" {
  type    = string
  default = "us-central1"
}
variable "api_image" { type = string }
variable "admin_image" { type = string }
variable "bucket_name" { type = string }
variable "admin_members" {
  type        = set(string)
  description = "IAP principals, for example user:admin@example.com"
}
variable "admin_emails" {
  type        = set(string)
  description = "Defense-in-depth email allowlist used by prana-admin"
}
variable "terraform_operator" {
  type        = string
  description = "IAM principal that manages Firebase, for example user:admin@example.com"
}
variable "billing_account" { type = string }
variable "google_idp_web_client_id" {
  type        = string
  default     = ""
  description = "Google OAuth Web client ID configured for the Identity Platform provider"
  validation {
    condition     = !var.manage_google_idp_provider || endswith(var.google_idp_web_client_id, ".apps.googleusercontent.com")
    error_message = "google_idp_web_client_id must be a Google OAuth client ID."
  }
}
variable "google_idp_web_client_secret" {
  type        = string
  default     = ""
  sensitive   = true
  description = "Google OAuth Web client secret; keep only in ignored tfvars and protected remote state"
}
variable "google_desktop_oauth_client_id" {
  type        = string
  description = "Public Desktop OAuth client ID bundled with Windows and Pi clients"
  validation {
    condition     = endswith(var.google_desktop_oauth_client_id, ".apps.googleusercontent.com")
    error_message = "google_desktop_oauth_client_id must be a Google OAuth client ID."
  }
}
variable "manage_google_idp_provider" {
  type        = bool
  default     = false
  description = "Manage the Google Identity Platform provider after Web OAuth credentials are supplied."
}
variable "google_desktop_oauth_secret_id" {
  type        = string
  default     = "prana-google-desktop-oauth-client-secret"
  description = "Existing Secret Manager secret containing the Desktop OAuth client secret."
}
variable "google_auth_instance_requests_per_minute" {
  type        = number
  default     = 60
  description = "Maximum Google OAuth exchanges per minute on each Cloud Run instance"
  validation {
    condition     = var.google_auth_instance_requests_per_minute >= 1 && var.google_auth_instance_requests_per_minute <= 10000
    error_message = "google_auth_instance_requests_per_minute must be between 1 and 10000."
  }
}
variable "google_auth_global_requests_per_minute" {
  type        = number
  default     = 300
  description = "Maximum Google OAuth exchanges per minute across all API instances"
  validation {
    condition     = var.google_auth_global_requests_per_minute >= 1 && var.google_auth_global_requests_per_minute <= 10000
    error_message = "google_auth_global_requests_per_minute must be between 1 and 10000."
  }
}
variable "budget_currency_code" { type = string }
variable "monthly_budget_amount" {
  type = number
  validation {
    condition     = var.monthly_budget_amount > 0
    error_message = "A positive monthly budget alert amount is required."
  }
}
variable "global_daily_audio_seconds" {
  type = number
  validation {
    condition     = var.global_daily_audio_seconds > 0
    error_message = "The daily circuit breaker must be positive."
  }
}
variable "global_monthly_audio_seconds" {
  type = number
  validation {
    condition     = var.global_monthly_audio_seconds > 0
    error_message = "The monthly circuit breaker must be positive."
  }
}
variable "input_cost_per_million_tokens" { type = number }
variable "output_cost_per_million_tokens" { type = number }
variable "api_max_instance_count" {
  type    = number
  default = 2
}
variable "admin_max_instance_count" {
  type    = number
  default = 1
}
variable "manage_project_key_policies" {
  type        = bool
  default     = false
  description = "Create project-level key policies only when the operator has Organization Policy Admin."
}
