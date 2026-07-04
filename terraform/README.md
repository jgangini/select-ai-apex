# Terraform Package

This package creates or references Oracle Autonomous Database resources for
Select AI APEX deployments. The APEX application is installed by the
`select-ai-apex` CLI after a wallet is available.

OCI user, fingerprint, and key-path variables are optional: local CLI runs can provide them, while OCI Resource Manager uses its managed provider authentication. Deploy Studio supplies the database passwords and invokes the repository-owned post-apply hook; local CLI runs may leave the infrastructure passwords empty to use Terraform-generated values.

Typical flow for a new database:

```powershell
select-ai-apex plan --mode new --oci-config .oci/config --oci-key .oci/key.pem --oci-compartment-id ocid1.compartment.oc1..aaaa --schemas HR
terraform -chdir=terraform init
terraform -chdir=terraform apply -var-file=../outputs/terraform.tfvars.json
terraform -chdir=terraform output -raw adb_wallet_base64 > ../outputs/adb_wallet.b64
terraform -chdir=terraform output -raw adb_admin_password > ../outputs/adb-admin-password.txt
terraform -chdir=terraform output -raw adb_wallet_password > ../outputs/wallet-password.txt
```

Decode `outputs/adb_wallet.b64` to `outputs/adb_wallet.zip`, then run
`select-ai-apex install` with the generated wallet and passwords.
