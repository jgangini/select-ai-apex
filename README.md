# Select AI APEX

Automated deployment project for Oracle Select AI on Autonomous Database `19c` or `26ai`, with the final user experience delivered as an Oracle APEX application.

Select AI APEX is an independent deployment project. Terraform creates or references Autonomous Database resources, and the CLI connects through a wallet, prepares the Select AI profile schema, imports the APEX export, and writes an auditable report of what was executed.

## What It Deploys

- Autonomous Database `19c` or `26ai`, new or existing.
- A parsing/profile schema named `SELECT_AI_APP`.
- Object-level grants for the schemas or tables you want Select AI to analyze.
- OCI Generative AI credential using OCI `config` and `key.pem`.
- Select AI profile `GROK_REASONING` using `xai.grok-4-fast-reasoning` by default.
- APEX workspace `SELECT_AI_APEX` and app alias `SELECT_AI_APEX`.
- The upstream APEX export from `oracle-ai/select-ai-openai`.

## Install Locally

```powershell
py -3.11 -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
$env:PYTHONPATH = "installer"
.\.venv\Scripts\python.exe -m select_ai_apex.cli --help
```

If you install the package, the console script is:

```powershell
pip install -e .
select-ai-apex --help
```

## Existing Database

Use this when the Autonomous Database already exists. You provide wallet, ADMIN credentials, and the schemas or tables that Select AI can inspect.

```powershell
select-ai-apex install `
  --mode existing `
  --wallet .\wallet.zip `
  --wallet-password "<wallet-password>" `
  --admin-user ADMIN `
  --admin-password "<admin-password>" `
  --oci-config .\.oci\config `
  --oci-key .\.oci\key.pem `
  --schemas HR `
  --tables HR.EMPLOYEES,HR.DEPARTMENTS
```

If `--dsn` is omitted, the CLI reads `tnsnames.ora` inside the wallet and picks the first alias.

## New Database

For a new database, start with only OCI `config`, `key.pem`, and a target compartment. The CLI generates SQL and Terraform variables, then Terraform creates the database and wallet.

```powershell
select-ai-apex plan `
  --mode new `
  --oci-config .\.oci\config `
  --oci-key .\.oci\key.pem `
  --oci-compartment-id ocid1.compartment.oc1..aaaa `
  --db-version 26ai `
  --workload OLTP `
  --schemas HR

terraform -chdir=terraform init
terraform -chdir=terraform apply -var-file=..\outputs\terraform.tfvars.json
terraform -chdir=terraform output -raw adb_wallet_base64 > .\outputs\adb_wallet.b64
terraform -chdir=terraform output -raw adb_admin_password > .\outputs\adb-admin-password.txt
terraform -chdir=terraform output -raw adb_wallet_password > .\outputs\wallet-password.txt
```

Decode the wallet:

```powershell
$walletB64 = Get-Content .\outputs\adb_wallet.b64 -Raw
[IO.File]::WriteAllBytes((Resolve-Path .\outputs).Path + "\adb_wallet.zip", [Convert]::FromBase64String($walletB64))
```

Then run the installer:

```powershell
select-ai-apex install `
  --mode new `
  --wallet .\outputs\adb_wallet.zip `
  --wallet-password (Get-Content .\outputs\wallet-password.txt -Raw).Trim() `
  --admin-user ADMIN `
  --admin-password (Get-Content .\outputs\adb-admin-password.txt -Raw).Trim() `
  --oci-config .\.oci\config `
  --oci-key .\.oci\key.pem `
  --schemas HR
```

## Generated Outputs

The CLI writes:

- `outputs/01_admin_bootstrap.sql`
- `outputs/02_select_ai_profile.sql`
- `outputs/03_apex_import_prelude.sql`
- `outputs/04_apex_post_install.sql`
- `outputs/executed-steps.sql`
- `outputs/deployment-report.md`
- `outputs/secrets.json`
- `outputs/terraform.tfvars.json`

`outputs/` is ignored by git.

## Access Model

The generated SQL does not use `SELECT ANY TABLE`. Access is controlled by grants to `SELECT_AI_APP`.

For new databases, Oracle-maintained sample schemas such as `SH` can be readable by `ADMIN` but still not grantable or unlockable as application source schemas. In that case the generated SQL creates a normal demo schema such as `SH_DEMO`, copies the selected sample tables into it, grants `SH_DEMO` to `SELECT_AI_APP`, and points the Select AI profile to `SH_DEMO`.

To add more data later:

```sql
GRANT SELECT ON HR.NEW_TABLE TO SELECT_AI_APP;
```

Then re-run the profile step:

```powershell
select-ai-apex plan --mode existing --wallet .\wallet.zip --oci-config .\.oci\config --oci-key .\.oci\key.pem --schemas HR
```

Run `outputs/02_select_ai_profile.sql` as `SELECT_AI_APP`, or re-run `install`.

## Verification

Without installing dev dependencies:

```powershell
$env:PYTHONPATH = "installer"
py -3.11 -m unittest discover -s tests -v
```

With the bundled Codex Python runtime, pass the runtime path to:

```powershell
.\scripts\check-project.ps1 -Python "C:\path\to\python.exe"
```

## Sources

See [docs/official-sources.md](docs/official-sources.md).

## License

This project is licensed under the MIT License.

Select AI APEX is an independent project and is not an official Oracle
product. It is not affiliated with, endorsed by, or sponsored by Oracle
Corporation. Oracle, OCI, APEX, and related marks are trademarks or registered
trademarks of Oracle and/or its affiliates. Third-party trademarks, logos,
service names, and assets remain the property of their respective owners.
