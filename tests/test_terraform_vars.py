from pathlib import Path
import unittest

from installer.models import DeploymentOptions
from installer.oci_config import OciConfig
from installer.terraform_vars import terraform_tfvars


class TerraformVarsTests(unittest.TestCase):
    def test_tfvars_include_new_database_mode_without_compute_assumptions(self) -> None:
        options = DeploymentOptions(
            mode="new",
            oci_config=OciConfig(
                tenancy="ocid1.tenancy.oc1..aaaa",
                user="ocid1.user.oc1..bbbb",
                fingerprint="aa:bb",
                region="us-chicago-1",
            ),
            oci_private_key="key",
            schemas=["HR"],
            tables=[],
            app_schema_password="SchemaPass123",
            apex_password="ApexPass123",
            oci_compartment_id="ocid1.compartment.oc1..cccc",
            db_version="19c",
            workload="DW",
        )

        values = terraform_tfvars(options, Path("key.pem"))

        self.assertEqual(values["autonomous_database_mode"], "new")
        self.assertEqual(values["autonomous_database_version"], "19c")
        self.assertEqual(values["autonomous_database_workload"], "DW")
        self.assertNotIn("instance_shape", values)
