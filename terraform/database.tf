locals {
  create_autonomous_database = var.autonomous_database_mode == "new"
  autonomous_database_id     = local.create_autonomous_database ? oci_database_autonomous_database.select_ai_apex[0].id : var.existing_autonomous_database_ocid
  autonomous_database_dbname = local.create_autonomous_database ? oci_database_autonomous_database.select_ai_apex[0].db_name : data.oci_database_autonomous_database.existing[0].db_name
}

resource "random_password" "adb_admin_password" {
  count   = local.create_autonomous_database ? 1 : 0
  length  = 18
  special = false
}

resource "random_password" "adb_wallet_password" {
  count   = local.create_autonomous_database ? 1 : 0
  length  = 18
  special = false
}

data "oci_database_autonomous_database" "existing" {
  count = local.create_autonomous_database ? 0 : 1

  autonomous_database_id = var.existing_autonomous_database_ocid
}

resource "oci_database_autonomous_database" "select_ai_apex" {
  count = local.create_autonomous_database ? 1 : 0

  admin_password = random_password.adb_admin_password[0].result
  compartment_id = var.compartment_ocid
  db_name        = var.adb_db_name
  display_name   = var.adb_display_name

  compute_count            = var.compute_count
  compute_model            = "ECPU"
  data_storage_size_in_tbs = var.data_storage_size_in_tbs
  db_version               = var.autonomous_database_version
  db_workload              = var.autonomous_database_workload
  is_auto_scaling_enabled  = var.is_auto_scaling_enabled
}

resource "oci_database_autonomous_database_wallet" "adb_wallet" {
  count = local.create_autonomous_database ? 1 : 0

  autonomous_database_id = local.autonomous_database_id
  password               = random_password.adb_wallet_password[0].result

  base64_encode_content = true
}
