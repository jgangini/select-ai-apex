############################################
# Autonomous Database and wallet for Select AI Apex
############################################

locals {
  uses_existing_autonomous_database      = var.autonomous_database_mode == "existing"
  uploaded_autonomous_database_wallet    = "${path.module}/.oci/adb_wallet.zip"
  uses_uploaded_existing_database_wallet = local.uses_existing_autonomous_database && fileexists(local.uploaded_autonomous_database_wallet)
  autonomous_database_id                 = local.uses_existing_autonomous_database ? var.existing_autonomous_database_ocid : oci_database_autonomous_database.select_ai_apex[0].id
  autonomous_database_db_name            = local.uses_existing_autonomous_database ? data.oci_database_autonomous_database.existing_adb[0].db_name : oci_database_autonomous_database.select_ai_apex[0].db_name
  autonomous_database_connection_urls    = local.uses_existing_autonomous_database ? data.oci_database_autonomous_database.existing_adb[0].connection_urls : oci_database_autonomous_database.select_ai_apex[0].connection_urls
  autonomous_database_admin_password     = var.autonomous_database_admin_password != "" ? var.autonomous_database_admin_password : random_password.adb_admin_password[0].result
  autonomous_database_wallet_password    = var.autonomous_database_wallet_password != "" ? var.autonomous_database_wallet_password : random_password.adb_wallet_password[0].result
  adb_db_name                            = var.adb_db_name != "" ? var.adb_db_name : substr("sapx${var.deployment_suffix}", 0, 14)
  adb_display_name                       = var.adb_display_name != "" ? var.adb_display_name : "selectaiapex-${var.deployment_suffix}"
}

resource "random_password" "adb_admin_password" {
  count   = var.autonomous_database_admin_password == "" ? 1 : 0
  length  = 18
  special = false
}

resource "random_password" "adb_wallet_password" {
  count   = var.autonomous_database_wallet_password == "" ? 1 : 0
  length  = 18
  special = false
}

data "oci_database_autonomous_database" "existing_adb" {
  count = local.uses_existing_autonomous_database ? 1 : 0

  autonomous_database_id = var.existing_autonomous_database_ocid
}

resource "oci_database_autonomous_database" "select_ai_apex" {
  count = local.uses_existing_autonomous_database ? 0 : 1

  admin_password = local.autonomous_database_admin_password
  compartment_id = var.compartment_ocid
  db_name        = local.adb_db_name

  compute_count               = var._oci_autonomous_database.compute_count
  compute_model               = "ECPU"
  data_storage_size_in_tbs    = var._oci_autonomous_database.data_storage_size_in_tbs
  db_version                  = var.autonomous_database_version
  db_workload                 = var.autonomous_database_workload
  display_name                = local.adb_display_name
  is_auto_scaling_enabled     = var._oci_autonomous_database.is_auto_scaling_enabled
  is_dev_tier                 = false
  is_mtls_connection_required = true

  db_tools_details {
    name       = "APEX"
    is_enabled = true
  }

  db_tools_details {
    name       = "ORDS"
    is_enabled = true
  }
}

resource "oci_database_autonomous_database_wallet" "adb_wallet" {
  count = local.uses_uploaded_existing_database_wallet ? 0 : 1

  autonomous_database_id = local.autonomous_database_id
  password               = local.autonomous_database_wallet_password

  base64_encode_content = true
}
