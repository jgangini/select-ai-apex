# Tutorial

## Deploy the Sales History lab

You need access to [Deploy Studio](https://cloudtechnext.net/#deploy), an OCI config file and matching API signing key, and permission to use the target compartment, Resource Manager, Autonomous Database, and OCI Generative AI. Choose a subscribed region with an available chat model.

1. In **Deploy Studio**, choose **Select AI APEX** and [v1.3.8](https://github.com/jgangini/select-ai-apex/releases/tag/v1.3.8) or a newer release.
2. In **OCI Credentials**, attach the OCI config and API private key. In **Services to deploy**, select the OCI region and either create a compartment or choose an existing one.
3. In **Autonomous Database**, choose **Create new** and a 26ai profile. Set the database ADMIN and wallet passwords.
4. Choose a **Generative AI chat model** and an **APEX application**. Choose **Chat DB** for APEX 24.1 or later, or **Ask Oracle 5.0.0.2** for APEX 26.1.6 or later. Select **Sales History (SH_DEMO)** as the schema to expose, set the workspace username, and enter its password.
5. Select **Validate**, then **Deploy**. Follow **Database plan**, **Database apply**, and **Select AI and APEX setup**. Wait for the job to succeed.
6. Open the application URL from the completed job. For Ask Oracle, the link opens the sign-in page with a fresh APEX session. Sign in with the APEX workspace credentials. A new Ask Oracle user starts in NL2SQL with the profile created by the installer. The Ask Oracle profile uses an 8,192-token generation limit. For table inventories it requests compact SQL scoped to the profile so the Explore report can display the list. Ask, “Show total sales by year.” Confirm the result uses the Sales History schema. Review the deployment report to check the model, data scope, and application alias. The access email lists the database name and ADMIN user before the Oracle APEX URL and workspace credentials. Its attachments include the database wallet, deployment report, execution log, and Terraform source.

For Ask Oracle, open **Admin Controls** from the application menu. The installer initializes the catalog map so the page can load before you create any catalogs.

**Core Banking** loads `FLEXCUBE_DEMO`. A sample question is “How many customer accounts are in each branch?” See the [demo catalog](../data/manifest.json) for schema contents and the [APEX catalog](../apex/manifest.json) for application compatibility.

## Use an existing Autonomous Database

In Deploy Studio, choose **Use existing** and select an available database in the chosen region. Enter its ADMIN password and choose a password for the wallet that OCI will generate. After Deploy Studio lists the source schemas, select the data to expose. Verify that ADMIN can grant access to those objects and that the database has the required APEX version and ORDS enabled. Choose the model, then validate and deploy.

OCI credentials must be allowed to list the database and generate its wallet. The backend also needs a network route to the database to list the schemas. [Autonomous Database IAM permissions](https://docs.oracle.com/en-us/iaas/autonomous-database-serverless/doc/autonomous-database-iam-policies.html)

The installer checks the APEX version before running setup SQL. Chat DB uses workspace `SELECT_AI_APEX` and parsing schema `SELECT_AI_APP`. Ask Oracle uses workspace `SELECT_AI_APEX_5002` and parsing schema `SELECT_AI_APP_5002`. Repeating a deployment reuses the application in its workspace.

## Run the installer from a workstation

Use Python 3.11 or later and work from the repository root. Install the CLI by following the [quick start](../README.md#quick-start). The `install` command connects to the database using a wallet. Here it scopes the profile to two tables in an existing database. Replace the example file paths and table names with your own values.

```powershell
$walletPassword = Read-Host 'Wallet password' -MaskInput
$adminPassword = Read-Host 'Database ADMIN password' -MaskInput
.\.venv\Scripts\select-ai-apex.exe install `
  --mode existing `
  --wallet .\.oci\wallet.zip `
  --wallet-password $walletPassword `
  --admin-user ADMIN `
  --admin-password $adminPassword `
  --oci-config .\.oci\config `
  --oci-key .\.oci\key.pem `
  --tables HR.EMPLOYEES,HR.DEPARTMENTS
```

Run the example in a private PowerShell 7 session. With no `--dsn`, the installer selects the first alias in the wallet's `tnsnames.ora`. Inspect `outputs/deployment-report.md` for the workspace, installed application ID, Select AI profile, and object list. The generated workspace password is in `outputs/secrets.json`. Protect the entire [generated output directory](security-model.md).

## Preview the deployment SQL

The `plan` command renders SQL and Terraform inputs locally. For a new Sales History database, use your OCI file paths and the target compartment OCID:

```powershell
$compartment = Read-Host 'Target compartment OCID'
.\.venv\Scripts\select-ai-apex.exe plan `
  --mode new `
  --oci-config .\.oci\config `
  --oci-key .\.oci\key.pem `
  --oci-compartment-id $compartment `
  --db-version 26ai `
  --workload LH `
  --schemas SH_DEMO
```

Review `outputs/deployment-report.md` for the scope and `outputs/executed-steps.sql` for the generated SQL. This command writes files locally. Use the guided Deploy Studio workflow to provision the database and install APEX with its wallet.
