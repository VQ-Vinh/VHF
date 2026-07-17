output "api_url" { value = var.deploy_services ? google_cloud_run_v2_service.api[0].uri : null }
output "admin_url" { value = var.deploy_services ? google_cloud_run_v2_service.admin[0].uri : null }
output "firebase_web_api_key" { value = data.google_firebase_web_app_config.desktop.api_key }
