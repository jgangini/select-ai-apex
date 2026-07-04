output "application_url" {
  description = "Select AI Apex APEX URL."
  value       = try(local.autonomous_database_connection_urls.apex_url, "")
}

output "adb_db_name" {
  description = "Autonomous Database name used by Select AI Apex."
  value       = local.autonomous_database_db_name
}

output "autonomous_database_id" {
  description = "Autonomous Database OCID used by Select AI Apex."
  value       = local.autonomous_database_id
}
