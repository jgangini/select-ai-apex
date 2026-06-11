from __future__ import annotations

import json
from pathlib import Path

from .models import DeploymentOptions


def terraform_tfvars(options: DeploymentOptions, key_path: Path) -> dict[str, object]:
    values: dict[str, object] = {
        "tenancy_ocid": options.oci_config.tenancy,
        "user_ocid": options.oci_config.user,
        "fingerprint": options.oci_config.fingerprint,
        "private_key_path": str(key_path),
        "region": options.oci_config.region,
        "autonomous_database_mode": options.mode,
        "autonomous_database_version": options.db_version,
        "autonomous_database_workload": options.workload,
    }
    if options.oci_compartment_id:
        values["compartment_ocid"] = options.oci_compartment_id
    if options.existing_autonomous_database_ocid:
        values["existing_autonomous_database_ocid"] = options.existing_autonomous_database_ocid
    return values


def write_terraform_tfvars(options: DeploymentOptions, key_path: Path, output_dir: Path) -> None:
    output_dir.mkdir(parents=True, exist_ok=True)
    rendered = json.dumps(terraform_tfvars(options, key_path), indent=2) + "\n"
    (output_dir / "terraform.tfvars.json").write_text(rendered, encoding="utf-8")
