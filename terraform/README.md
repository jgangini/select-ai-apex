# Terraform Package

The root `terraform/` package creates or references Autonomous Database for Select AI APEX. [The Deploy Studio contract](deploy-studio.json) points to the [post-apply hook](../deploy/hooks/post_apply.py), which uses a database wallet to run the Python installer after Terraform.

OCI Resource Manager uses its managed provider authentication. Local Terraform commands can instead use the optional OCI user, fingerprint, and key-path variables. Database naming defaults are derived from `deployment_suffix`. The older name variables remain available as compatibility overrides.

Terraform returns the APEX base URL, database name, and database OCID. The installer uses the wallet and passwords supplied for the run, then returns the installed application's direct URL. Use [Deploy Studio](../docs/tutorial.md) for the end-to-end flow and the [validation commands](../docs/testing.md) to check the package locally.
