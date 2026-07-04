provider "oci" {
  tenancy_ocid     = var.user_ocid != "" ? var.tenancy_ocid : null
  user_ocid        = var.user_ocid != "" ? var.user_ocid : null
  fingerprint      = var.fingerprint != "" ? var.fingerprint : null
  private_key_path = var.private_key_path != "" ? var.private_key_path : null
  region           = var.region
}
