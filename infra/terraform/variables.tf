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
