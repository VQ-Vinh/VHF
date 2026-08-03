output "api_url" { value = var.deploy_services ? google_cloud_run_v2_service.api[0].uri : null }
output "admin_url" { value = var.deploy_services ? google_cloud_run_v2_service.admin[0].uri : null }
output "firebase_web_api_key" { value = data.google_firebase_web_app_config.desktop.api_key }
output "google_desktop_oauth_client_id" { value = var.google_desktop_oauth_client_id }
output "github_workload_identity_provider" {
  value = google_iam_workload_identity_pool_provider.github.name
}
output "github_deployer_service_account" {
  value = google_service_account.deployer.email
}
output "github_terraform_service_account" {
  value = google_service_account.terraform_ci.email
}
output "github_release_reader_service_account" {
  value = google_service_account.release_reader.email
}
