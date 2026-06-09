output "autonomous_database_id" {
  description = "Autonomous Database OCID."
  value       = local.autonomous_database_id
}

output "adb_db_name" {
  description = "Autonomous Database db_name."
  value       = local.autonomous_database_dbname
}

output "adb_admin_password" {
  description = "Generated ADMIN password for new database deployments."
  value       = local.create_autonomous_database ? random_password.adb_admin_password[0].result : ""
  sensitive   = true
}

output "adb_wallet_password" {
  description = "Generated wallet password for new database deployments."
  value       = local.create_autonomous_database ? random_password.adb_wallet_password[0].result : ""
  sensitive   = true
}

output "adb_wallet_base64" {
  description = "Generated wallet zip content as base64 for new database deployments."
  value       = local.create_autonomous_database ? oci_database_autonomous_database_wallet.adb_wallet[0].content : ""
  sensitive   = true
}
