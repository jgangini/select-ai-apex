# Testing

Run the following from the repository root. Use Python 3.11, PowerShell, and Terraform. Graphify and Sentrux support the local architecture checks.

## Before a change

```powershell
.\scripts\arch-preflight.ps1
```

## Local checks

```powershell
.\scripts\check-project.ps1 -Python python
python scripts/validate_demo_catalog.py
terraform -chdir=terraform fmt -check -recursive
terraform -chdir=terraform init -backend=false -input=false
terraform -chdir=terraform validate
```

Point `-Python` at a Python 3.11 executable if `python` uses a different interpreter. The Python suite uses `unittest` and synthetic fixtures for profile SQL, object grants, wallet handling, the Deploy Studio contract, hook output, and selected source assets. The catalog check validates the metadata and CSV layout for the bundled schemas. Terraform initialization downloads the required providers. [Python checks](../.github/workflows/checks.yml) · [Terraform checks](../.github/workflows/terraform.yml)

With the OCI Deploy Studio plugin and a CloudTechNext checkout available, run `python <plugin-script-path>/deploy_studio.py check . --studio <cloudtechnext-checkout>` to validate the manifest against the platform parser.

## After a change

```powershell
.\scripts\arch-postflight.ps1
```

Graphify's report at `graphify-out/GRAPH_REPORT.md` helps trace how the installer, manifests, and tests fit together. Sentrux compares the current structure against the local preflight baseline. The generated graph and baseline are local artifacts.

## OCI acceptance

Use the [live acceptance checklist](live-acceptance.md) to verify the installed APEX application, the selected database workload, and the Select AI data scope in a test compartment.
