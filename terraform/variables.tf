variable "tenancy_ocid" {
  description = "OCI tenancy OCID from the uploaded config file."
  type        = string
}

variable "user_ocid" {
  description = "OCI user OCID from the uploaded config file."
  type        = string
}

variable "fingerprint" {
  description = "OCI API key fingerprint from the uploaded config file."
  type        = string
}

variable "private_key_path" {
  description = "Local path to key.pem."
  type        = string
}

variable "region" {
  description = "OCI region, for example us-chicago-1."
  type        = string
}

variable "compartment_ocid" {
  description = "Target compartment OCID for a new Autonomous Database."
  type        = string
  default     = ""
}

variable "autonomous_database_mode" {
  description = "Whether to create a new Autonomous Database or reference an existing one."
  type        = string
  default     = "new"

  validation {
    condition     = contains(["new", "existing"], var.autonomous_database_mode)
    error_message = "autonomous_database_mode must be new or existing."
  }
}

variable "existing_autonomous_database_ocid" {
  description = "Existing Autonomous Database OCID when autonomous_database_mode is existing."
  type        = string
  default     = ""
}

variable "autonomous_database_version" {
  description = "Autonomous Database version to provision."
  type        = string
  default     = "26ai"

  validation {
    condition     = contains(["19c", "26ai"], var.autonomous_database_version)
    error_message = "autonomous_database_version must be 19c or 26ai."
  }
}

variable "autonomous_database_workload" {
  description = "Autonomous workload to provision."
  type        = string
  default     = "OLTP"

  validation {
    condition     = contains(["OLTP", "DW"], var.autonomous_database_workload)
    error_message = "autonomous_database_workload must be OLTP or DW."
  }
}

variable "adb_db_name" {
  description = "Autonomous Database db_name for new deployments."
  type        = string
  default     = "selaiapex"

  validation {
    condition     = can(regex("^[A-Za-z][A-Za-z0-9]{1,13}$", var.adb_db_name))
    error_message = "adb_db_name must start with a letter and be at most 14 alphanumeric characters."
  }
}

variable "adb_display_name" {
  description = "Autonomous Database display name for new deployments."
  type        = string
  default     = "select-ai-apex"
}

variable "compute_count" {
  description = "ECPU count for a new Autonomous Database."
  type        = number
  default     = 2
}

variable "data_storage_size_in_tbs" {
  description = "Storage size for a new Autonomous Database."
  type        = number
  default     = 1
}

variable "is_auto_scaling_enabled" {
  description = "Enable Autonomous Database auto scaling."
  type        = bool
  default     = true
}
